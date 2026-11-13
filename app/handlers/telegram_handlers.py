import asyncio
import logging

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from app.domain.journey import Riddle
from app.infrastructure.database import UserProgressRepository
from app.services.game_service import GameService

logger = logging.getLogger(__name__)


class JourneyBot:
    def __init__(self, repository: UserProgressRepository, levels: list[Riddle]):
        self.repository = repository
        self.game_service = GameService(repository, levels)
        self.router = Router(name="journey")
        self._timer_tasks: dict[int, asyncio.Task] = {}
        self._register_handlers()

    def _register_handlers(self) -> None:
        self.router.message.register(self.start, Command("start"))
        self.router.message.register(self.stats, Command("stats"))
        self.router.message.register(self.leaderboard, Command("leaderboard"))
        self.router.callback_query.register(self.handle_callback)
        self.router.message.register(self.handle_text, F.text)

    @staticmethod
    def _identity(user) -> tuple[str | None, str]:
        display = " ".join(part for part in [user.first_name, user.last_name] if part).strip()
        return user.username, display or f"Игрок {user.id}"

    def _progress(self, user) -> dict:
        username, display = self._identity(user)
        return self.repository.ensure_player(user.id, username, display)

    def _cancel_timer(self, user_id: int) -> None:
        task = self._timer_tasks.pop(user_id, None)
        if task and not task.done():
            task.cancel()

    def _start_timer(self, bot: Bot, user_id: int, chat_id: int, message_id: int) -> None:
        self._cancel_timer(user_id)
        self._timer_tasks[user_id] = asyncio.create_task(
            self._timer_loop(bot, user_id, chat_id, message_id),
            name=f"journey-timer:{user_id}",
        )

    async def _send_level(
        self, message: Message, bot: Bot, level: int, user_id: int | None = None
    ) -> None:
        # Callback messages are authored by the bot; use the callback user's ID
        # when this method is called from an inline-button handler.
        user_id = user_id if user_id is not None else message.from_user.id
        card = await message.answer(
            self.game_service.get_stage_intro(level, user_id),
            reply_markup=self.game_service.build_inline_keyboard(level),
        )
        self._start_timer(bot, user_id, card.chat.id, card.message_id)

    async def start(self, message: Message) -> None:
        user = message.from_user
        username, display = self._identity(user)
        self._cancel_timer(user.id)
        self.repository.start_game(user.id, username, display)
        await message.answer(
            self.game_service.get_start_message(),
            reply_markup=self.game_service.build_inline_keyboard(1, "welcome"),
        )

    async def stats(self, message: Message) -> None:
        user = message.from_user
        self._progress(user)
        row = self.repository.get_player_stats(user.id)
        progress = self.repository.get_progress(user.id)
        active_level = progress["level"] if progress and not progress["completed"] else 0
        text = (
            f"📊 Статистика игрока {self._identity(user)[1]}\n\n"
            f"🚀 Запусков: {row['games_started']}\n"
            f"🏆 Завершённых путешествий: {row['games_completed']}\n"
            f"⭐ Лучшее время: {self.game_service.format_duration(row['best_time_seconds'])}\n"
            f"🧩 Всего ответов: {row['total_attempts']}\n"
            f"⌛ Истекло таймеров: {row['timeouts']}\n"
            f"🎮 Текущий уровень: {active_level or 'нет активной игры'}"
        )
        await message.answer(text)

    async def leaderboard(self, message: Message) -> None:
        rows = self.repository.get_leaderboard()
        if not rows:
            await message.answer("🏅 Таблица лидеров\n\nПока нет завершённых путешествий — стань первым!")
            return
        lines = ["🏅 Таблица лидеров — лучшее время", ""]
        for index, row in enumerate(rows, start=1):
            name = row["display_name"] or (f"@{row['username']}" if row["username"] else "Путешественник")
            lines.append(f"{index}. {name} — {self.game_service.format_duration(row['best_time_seconds'])} · 🏆 {row['games_completed']}")
        await message.answer("\n".join(lines))

    async def handle_text(self, message: Message, bot: Bot) -> None:
        user = message.from_user
        progress = self._progress(user)
        if progress["completed"]:
            await message.answer("🏁 Путешествие уже завершено. Используй /start для нового раунда или /stats для статистики.")
            return
        level = int(progress["level"])
        if not 1 <= level <= self.game_service.total_levels:
            level = 1
            self.repository.move_to_level(user.id, level)
        riddle = self.game_service.get_level(level)
        if self.repository.get_remaining_seconds(user.id, riddle.time_limit_seconds) <= 0:
            await self._handle_timeout(message, bot, user.id, level)
            return
        result = self.game_service.resolve_answer(level, message.text or "")
        self.repository.record_attempt(user.id, result["is_correct"])
        await self._apply_result(message, bot, user.id, level, result)

    async def handle_callback(self, query: CallbackQuery, bot: Bot) -> None:
        await query.answer()
        user = query.from_user
        data = query.data or ""

        if data == "restart":
            username, display = self._identity(user)
            self._cancel_timer(user.id)
            self.repository.start_game(user.id, username, display)
            if query.message:
                await query.message.edit_text(
                    self.game_service.get_start_message(),
                    reply_markup=self.game_service.build_inline_keyboard(1, "welcome"),
                )
            return

        progress = self._progress(user)
        level = int(progress["level"])
        if data == "begin":
            if query.message:
                # Start the level countdown when the player opens the first riddle,
                # not when /start displays the welcome screen.
                self.repository.move_to_level(user.id, level)
                await self._send_level(query.message, bot, level, user.id)
            return
        if data == "stats":
            row = self.repository.get_player_stats(user.id)
            await query.message.answer(
                f"📊 Завершено: {row['games_completed']} · Лучшее время: "
                f"{self.game_service.format_duration(row['best_time_seconds'])} · Попыток: {row['total_attempts']}"
            )
            return
        if data == "leaderboard":
            if query.message:
                await self.leaderboard(query.message)
            return
        if data == "map":
            if query.message:
                await query.message.edit_text(
                    self.game_service.map_text(level, bool(progress["completed"])),
                    reply_markup=self.game_service.build_inline_keyboard(level, "map"),
                )
            return
        if data == "back":
            if query.message and not progress["completed"]:
                await query.message.edit_text(
                    self.game_service.get_stage_intro(level, user.id),
                    reply_markup=self.game_service.build_inline_keyboard(level),
                )
                self._start_timer(bot, user.id, query.message.chat.id, query.message.message_id)
            elif query.message:
                await query.message.edit_text(self.game_service.final_card(0))
            return
        if data == "retry":
            if query.message and not progress["completed"]:
                await query.message.edit_text(
                    self.game_service.get_stage_intro(level, user.id),
                    reply_markup=self.game_service.build_inline_keyboard(level),
                )
                self._start_timer(bot, user.id, query.message.chat.id, query.message.message_id)
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
            riddle = self.game_service.get_level(level)
            if self.repository.get_remaining_seconds(user.id, riddle.time_limit_seconds) <= 0:
                await self._handle_timeout_callback(query, bot, user.id, level)
                return
            result = self.game_service.resolve_answer(level, option)
            self.repository.record_attempt(user.id, result["is_correct"])
            if not result["is_correct"]:
                # Callback alerts are user-facing; log incorrect button selections for operators too.
                logger.info(
                    "Incorrect button answer from player %s (@%s) on level %s",
                    user.id,
                    user.username or "unknown",
                    level,
                )
            await self._apply_callback_result(query, bot, user.id, level, result)

    async def _apply_result(self, message: Message, bot: Bot, user_id: int, level: int, result: dict) -> None:
        if not result["is_correct"]:
            await message.answer(result["message"])
            return
        self._cancel_timer(user_id)
        if result["finished"]:
            elapsed = self.repository.mark_completed(user_id)
            await message.answer(
                self.game_service.final_card(elapsed),
                reply_markup=self.game_service.build_inline_keyboard(level, "finished"),
            )
            return
        next_level = result["next_level"]
        self.repository.move_to_level(user_id, next_level)
        await message.answer(result["message"])
        await self._send_level(message, bot, next_level, user_id)

    async def _apply_callback_result(self, query: CallbackQuery, bot: Bot, user_id: int, level: int, result: dict) -> None:
        message = query.message
        if not message:
            return
        if not result["is_correct"]:
            await query.answer(result["message"], show_alert=True)
            return
        self._cancel_timer(user_id)
        if result["finished"]:
            elapsed = self.repository.mark_completed(user_id)
            await message.edit_text(result["message"])
            await message.answer(
                self.game_service.final_card(elapsed),
                reply_markup=self.game_service.build_inline_keyboard(level, "finished"),
            )
            return
        next_level = result["next_level"]
        self.repository.move_to_level(user_id, next_level)
        await message.edit_text(result["message"])
        await self._send_level(message, bot, next_level, user_id)

    async def _handle_timeout(self, message: Message, bot: Bot, user_id: int, level: int) -> None:
        self.repository.record_timeout(user_id)
        await message.answer("⌛ Время вышло! Уровень не потерян — отсчёт начался заново.")
        await self._send_level(message, bot, level, user_id)

    async def _handle_timeout_callback(self, query: CallbackQuery, bot: Bot, user_id: int, level: int) -> None:
        self._cancel_timer(user_id)
        self.repository.record_timeout(user_id)
        if query.message:
            await query.message.edit_text(
                "⌛ Время вышло! Уровень не потерян — отсчёт начался заново.\n\n"
                + self.game_service.get_stage_intro(level, user_id),
                reply_markup=self.game_service.build_inline_keyboard(level),
            )
            self._start_timer(bot, user_id, query.message.chat.id, query.message.message_id)

    async def _timer_loop(self, bot: Bot, user_id: int, chat_id: int, message_id: int) -> None:
        try:
            while True:
                progress = self.repository.get_progress(user_id)
                if not progress or progress["completed"]:
                    return
                level = int(progress["level"])
                if not 1 <= level <= self.game_service.total_levels:
                    return
                riddle = self.game_service.get_level(level)
                remaining = self.repository.get_remaining_seconds(user_id, riddle.time_limit_seconds)
                if remaining <= 0:
                    self.repository.record_timeout(user_id)
                    text = "⌛ Время вышло! Уровень не потерян — отсчёт начался заново.\n\n"
                    text += self.game_service.get_stage_intro(level, user_id)
                else:
                    text = self.game_service.get_stage_intro(level, user_id)
                try:
                    await bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=message_id,
                        text=text,
                        reply_markup=self.game_service.build_inline_keyboard(level),
                    )
                except TelegramBadRequest as exc:
                    if "message is not modified" not in str(exc).lower():
                        logger.info("Timer stopped for player %s: %s", user_id, exc)
                        return
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            raise
        finally:
            current = self._timer_tasks.get(user_id)
            if current is asyncio.current_task():
                self._timer_tasks.pop(user_id, None)

    async def shutdown(self) -> None:
        tasks = list(self._timer_tasks.values())
        self._timer_tasks.clear()
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)


def build_router(repository: UserProgressRepository, levels: list[Riddle]) -> JourneyBot:
    return JourneyBot(repository, levels)
