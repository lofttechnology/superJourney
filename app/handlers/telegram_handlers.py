from telegram import Update
from telegram.error import BadRequest
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from app.domain.journey import Riddle
from app.infrastructure.database import UserProgressRepository
from app.services.game_service import GameService

TIMER_JOB_PREFIX = "journey-timer:"


class JourneyBot:
    def __init__(self, repository: UserProgressRepository, levels: list[Riddle]):
        self.repository = repository
        self.game_service = GameService(repository, levels)

    def _identity(self, user) -> tuple[str | None, str]:
        display = " ".join(part for part in [user.first_name, user.last_name] if part).strip()
        return user.username, display or f"Игрок {user.id}"

    def _progress(self, user) -> dict:
        username, display = self._identity(user)
        return self.repository.ensure_player(user.id, username, display)

    def _cancel_timer(self, context: ContextTypes.DEFAULT_TYPE, user_id: int) -> None:
        for job in context.job_queue.get_jobs_by_name(f"{TIMER_JOB_PREFIX}{user_id}"):
            job.schedule_removal()

    def _schedule_timer(self, context: ContextTypes.DEFAULT_TYPE, user_id: int, chat_id: int, message_id: int) -> None:
        self._cancel_timer(context, user_id)
        context.job_queue.run_repeating(
            self._timer_tick,
            interval=1,
            first=1,
            name=f"{TIMER_JOB_PREFIX}{user_id}",
            data={"user_id": user_id, "chat_id": chat_id, "message_id": message_id},
        )

    async def _send_level(self, update: Update, context: ContextTypes.DEFAULT_TYPE, level: int) -> None:
        user = update.effective_user
        intro = self.game_service.get_stage_intro(level, user.id)
        keyboard = self.game_service.build_inline_keyboard(level)
        message = await update.effective_message.reply_text(intro, reply_markup=keyboard, parse_mode="Markdown")
        self._schedule_timer(context, user.id, message.chat_id, message.message_id)

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        username, display = self._identity(user)
        self._cancel_timer(context, user.id)
        self.repository.start_game(user.id, username, display)
        keyboard = self.game_service.build_inline_keyboard(1, "welcome")
        await update.effective_message.reply_text(
            self.game_service.get_start_message(), reply_markup=keyboard, parse_mode="Markdown"
        )

    async def stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        self._progress(user)
        row = self.repository.get_player_stats(user.id)
        progress = self.repository.get_progress(user.id)
        completed = row["games_completed"]
        active_level = progress["level"] if progress and not progress["completed"] else 0
        text = (
            f"📊 *Статистика игрока {self._identity(user)[1]}*\n\n"
            f"🚀 Запусков: {row['games_started']}\n"
            f"🏆 Завершённых путешествий: {completed}\n"
            f"⭐ Лучшее время: {self.game_service.format_duration(row['best_time_seconds'])}\n"
            f"🧩 Всего ответов: {row['total_attempts']}\n"
            f"⌛ Истекло таймеров: {row['timeouts']}\n"
            f"🎮 Текущий уровень: {active_level or 'нет активной игры'}"
        )
        await update.effective_message.reply_text(text, parse_mode="Markdown")

    async def leaderboard(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        rows = self.repository.get_leaderboard()
        if not rows:
            text = "🏅 *Таблица лидеров*\n\nПока нет завершённых путешествий — стань первым!"
        else:
            lines = ["🏅 *Таблица лидеров — лучшее время*", ""]
            for index, row in enumerate(rows, start=1):
                name = row["display_name"] or (f"@{row['username']}" if row["username"] else "Путешественник")
                duration = self.game_service.format_duration(row["best_time_seconds"])
                lines.append(f"{index}. {name} — {duration} · 🏆 {row['games_completed']}")
            text = "\n".join(lines)
        await update.effective_message.reply_text(text, parse_mode="Markdown")

    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        progress = self._progress(user)
        if progress["completed"]:
            await update.effective_message.reply_text(
                "🏁 Путешествие уже завершено. Используй /start для нового раунда или /stats для статистики."
            )
            return
        level = int(progress["level"])
        if not 1 <= level <= self.game_service.total_levels:
            level = 1
            self.repository.move_to_level(user.id, level)
        result = self.game_service.resolve_answer(level, update.effective_message.text or "")
        if self.repository.get_remaining_seconds(user.id, self.game_service.get_level(level).time_limit_seconds) <= 0:
            await self._handle_timeout(update, context, user.id, level)
            return
        self.repository.record_attempt(user.id, result["is_correct"])
        await self._apply_result(update, context, user.id, level, result)

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        await query.answer()
        user = query.from_user
        data = query.data or ""

        if data == "restart":
            username, display = self._identity(user)
            self._cancel_timer(context, user.id)
            self.repository.start_game(user.id, username, display)
            await query.edit_message_text(self.game_service.get_start_message(), parse_mode="Markdown")
            await query.message.reply_text(
                "🧭 Готов? Нажми «Начать путешествие» в сообщении выше, чтобы открыть первый уровень."
            )
            return

        progress = self._progress(user)
        level = int(progress["level"])
        if data == "begin":
            await self._send_level(update, context, level)
            return
        if data == "stats":
            stats = self.repository.get_player_stats(user.id)
            await query.message.reply_text(
                f"📊 Завершено: {stats['games_completed']} · Лучшее время: "
                f"{self.game_service.format_duration(stats['best_time_seconds'])} · "
                f"Попыток: {stats['total_attempts']}"
            )
            return
        if data == "leaderboard":
            await self.leaderboard(update, context)
            return
        if data == "map":
            await query.edit_message_text(
                self.game_service.map_text(level, bool(progress["completed"])),
                reply_markup=self.game_service.build_inline_keyboard(level, "map"),
                parse_mode="Markdown",
            )
            return
        if data == "back":
            if progress["completed"]:
                await query.edit_message_text(self.game_service.final_card(0), parse_mode="Markdown")
                return
            await query.edit_message_text(
                self.game_service.get_stage_intro(level, user.id),
                reply_markup=self.game_service.build_inline_keyboard(level),
                parse_mode="Markdown",
            )
            self._schedule_timer(context, user.id, query.message.chat_id, query.message.message_id)
            return
        if data == "retry":
            if not progress["completed"]:
                await query.edit_message_text(
                    self.game_service.get_stage_intro(level, user.id),
                    reply_markup=self.game_service.build_inline_keyboard(level),
                    parse_mode="Markdown",
                )
                self._schedule_timer(context, user.id, query.message.chat_id, query.message.message_id)
            return
        if data.startswith("answer:"):
            try:
                _, button_level, option_index = data.split(":", 2)
                button_level, option_index = int(button_level), int(option_index)
                if button_level != level:
                    await query.answer("Этот вариант от предыдущего уровня уже не активен.", show_alert=True)
                    return
                option = self.game_service.get_level(level).options[option_index]
            except (ValueError, IndexError):
                await query.answer("Не удалось распознать вариант ответа. Откройте уровень снова.", show_alert=True)
                return
            result = self.game_service.resolve_answer(level, option)
            if self.repository.get_remaining_seconds(user.id, self.game_service.get_level(level).time_limit_seconds) <= 0:
                await self._handle_timeout_callback(update, context, user.id, level)
                return
            self.repository.record_attempt(user.id, result["is_correct"])
            await self._apply_callback_result(update, context, user.id, level, result)

    async def _apply_result(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, level: int, result: dict) -> None:
        if not result["is_correct"]:
            await update.effective_message.reply_text(result["message"])
            return
        self._cancel_timer(context, user_id)
        if result["finished"]:
            elapsed = self.repository.mark_completed(user_id)
            await update.effective_message.reply_text(
                self.game_service.final_card(elapsed),
                reply_markup=self.game_service.build_inline_keyboard(level, "finished"),
                parse_mode="Markdown",
            )
            return
        next_level = result["next_level"]
        self.repository.move_to_level(user_id, next_level)
        await update.effective_message.reply_text(result["message"])
        await self._send_level(update, context, next_level)

    async def _apply_callback_result(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, level: int, result: dict) -> None:
        query = update.callback_query
        self._cancel_timer(context, user_id)
        if not result["is_correct"]:
            await query.edit_message_text(
                result["message"] + "\n\n" + self.game_service.get_stage_intro(level, user_id),
                reply_markup=self.game_service.build_inline_keyboard(level),
                parse_mode="Markdown",
            )
            self._schedule_timer(context, user_id, query.message.chat_id, query.message.message_id)
            return
        if result["finished"]:
            elapsed = self.repository.mark_completed(user_id)
            await query.edit_message_text(result["message"])
            await query.message.reply_text(
                self.game_service.final_card(elapsed),
                reply_markup=self.game_service.build_inline_keyboard(level, "finished"),
                parse_mode="Markdown",
            )
            return
        next_level = result["next_level"]
        self.repository.move_to_level(user_id, next_level)
        await query.edit_message_text(result["message"])
        await query.message.reply_text(
            self.game_service.get_stage_intro(next_level, user_id),
            reply_markup=self.game_service.build_inline_keyboard(next_level),
            parse_mode="Markdown",
        )
        message = await query.message.reply_text(
            "⏱ Таймер уровня запущен. Используй кнопки в карточке уровня выше.",
            disable_notification=True,
        )
        self._schedule_timer(context, user_id, message.chat_id, message.message_id)

    async def _handle_timeout(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, level: int) -> None:
        self.repository.record_timeout(user_id)
        await update.effective_message.reply_text("⌛ Время вышло! Уровень не потерян — таймер запущен заново.")
        await self._send_level(update, context, level)

    async def _handle_timeout_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, level: int) -> None:
        query = update.callback_query
        self._cancel_timer(context, user_id)
        self.repository.record_timeout(user_id)
        await query.edit_message_text("⌛ Время вышло! Уровень не потерян — таймер запущен заново.")
        await query.message.reply_text(
            self.game_service.get_stage_intro(level, user_id),
            reply_markup=self.game_service.build_inline_keyboard(level),
            parse_mode="Markdown",
        )
        message = await query.message.reply_text("⏱ Таймер уровня запущен.", disable_notification=True)
        self._schedule_timer(context, user_id, message.chat_id, message.message_id)

    async def _timer_tick(self, context: ContextTypes.DEFAULT_TYPE) -> None:
        job = context.job
        user_id = job.data["user_id"]
        progress = self.repository.get_progress(user_id)
        if not progress or progress["completed"]:
            job.schedule_removal()
            return
        level = int(progress["level"])
        if not 1 <= level <= self.game_service.total_levels:
            job.schedule_removal()
            return
        riddle = self.game_service.get_level(level)
        remaining = self.repository.get_remaining_seconds(user_id, riddle.time_limit_seconds)
        if remaining <= 0:
            self.repository.record_timeout(user_id)
            try:
                await context.bot.send_message(
                    chat_id=job.data["chat_id"],
                    text="⌛ Время вышло! Уровень не потерян — новый отсчёт начался.",
                )
                intro = self.game_service.get_stage_intro(level, user_id)
                message = await context.bot.send_message(
                    chat_id=job.data["chat_id"], text=intro,
                    reply_markup=self.game_service.build_inline_keyboard(level), parse_mode="Markdown",
                )
                self._schedule_timer(context, user_id, message.chat_id, message.message_id)
            finally:
                job.schedule_removal()
            return
        try:
            await context.bot.edit_message_text(
                chat_id=job.data["chat_id"],
                message_id=job.data["message_id"],
                text=self.game_service.get_stage_intro(level, user_id),
                reply_markup=self.game_service.build_inline_keyboard(level),
                parse_mode="Markdown",
            )
        except BadRequest as exc:
            if "message is not modified" not in str(exc).lower():
                job.schedule_removal()


def build_application(token: str, db_path: str, levels: list[Riddle]):
    repository = UserProgressRepository(db_path)
    bot = JourneyBot(repository, levels)
    app = ApplicationBuilder().token(token).build()
    app.add_handler(CommandHandler("start", bot.start))
    app.add_handler(CommandHandler("stats", bot.stats))
    app.add_handler(CommandHandler("leaderboard", bot.leaderboard))
    app.add_handler(CallbackQueryHandler(bot.handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), bot.handle_text))
    return app
