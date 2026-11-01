from datetime import datetime, timezone

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from app.config import get_settings
from app.domain.journey import JourneyState
from app.infrastructure.database import UserProgressRepository
from app.services.game_service import GameService


class JourneyBot:
    def __init__(self, repository: UserProgressRepository) -> None:
        self.repository = repository
        self.game_service = GameService(repository)

    def _get_user_state(self, user_id: int) -> JourneyState:
        row = self.repository.get_progress(user_id)
        if not row:
            return JourneyState.POINT_1
        return JourneyState(row["state"])

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user_id = update.effective_user.id
        self.repository.reset_progress(user_id)
        state = JourneyState.POINT_1
        self.repository.set_progress(user_id, state.value, 1)
        keyboard = self.game_service.build_inline_keyboard(state)
        await update.message.reply_text(
            self.game_service.get_start_message(),
            reply_markup=keyboard,
        )
        await update.message.reply_text(
            self.game_service.get_stage_intro(state, user_id),
            reply_markup=keyboard,
        )

    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user_id = update.effective_user.id
        text = (update.message.text or "").strip()
        if text.lower() in {"старт", "/start", "start"}:
            await self.start(update, context)
            return

        state = self._get_user_state(user_id)
        result = self.game_service.resolve_answer(state, text)
        next_state = result["next_state"]
        self.repository.set_progress(user_id, next_state.value, self.game_service.get_level_number(next_state))

        keyboard = self.game_service.build_inline_keyboard(next_state)
        await update.message.reply_text(result["message"], reply_markup=keyboard)

        if result["is_correct"] and next_state != JourneyState.FINISHED:
            await update.message.reply_text(
                self.game_service.get_stage_intro(next_state, user_id),
                reply_markup=keyboard,
            )
        elif result["is_correct"] and next_state == JourneyState.FINISHED:
            self.repository.mark_completed(user_id)
            await update.message.reply_text(self.game_service.build_final_victory(), reply_markup=keyboard)
        elif not result["is_correct"]:
            await update.message.reply_text(
                self.game_service.get_stage_intro(state, user_id),
                reply_markup=keyboard,
            )

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        data = query.data or ""

        if data == "restart":
            self.repository.reset_progress(user_id)
            state = JourneyState.POINT_1
            self.repository.set_progress(user_id, state.value, 1)
            keyboard = self.game_service.build_inline_keyboard(state)
            await query.edit_message_text(
                self.game_service.get_start_message(),
                reply_markup=keyboard,
            )
            await query.message.reply_text(
                self.game_service.get_stage_intro(state, user_id),
                reply_markup=keyboard,
            )
            return

        if data == "retry":
            state = self._get_user_state(user_id)
            keyboard = self.game_service.build_inline_keyboard(state)
            await query.edit_message_text(
                self.game_service.get_stage_intro(state, user_id),
                reply_markup=keyboard,
            )
            return

        if data == "map":
            await query.edit_message_text(self.game_service.get_map_text())
            return

        if data.startswith("answer:"):
            _, answer_value = data.split(":", 1)
            state = self._get_user_state(user_id)
            result = self.game_service.resolve_answer(state, answer_value)
            next_state = result["next_state"]
            self.repository.set_progress(user_id, next_state.value, self.game_service.get_level_number(next_state))

            keyboard = self.game_service.build_inline_keyboard(next_state)
            await query.edit_message_text(result["message"], reply_markup=keyboard)

            if result["is_correct"] and next_state != JourneyState.FINISHED:
                await query.message.reply_text(
                    self.game_service.get_stage_intro(next_state, user_id),
                    reply_markup=keyboard,
                )
            elif result["is_correct"] and next_state == JourneyState.FINISHED:
                self.repository.mark_completed(user_id)
                await query.message.reply_text(
                    self.game_service.build_final_victory(),
                    reply_markup=keyboard,
                )
            elif not result["is_correct"]:
                await query.message.reply_text(
                    self.game_service.get_stage_intro(state, user_id),
                    reply_markup=keyboard,
                )
            return


def build_application(token: str):
    repository = UserProgressRepository("data/superjourney.db")
    bot = JourneyBot(repository)
    app = ApplicationBuilder().token(token).build()
    app.add_handler(CommandHandler("start", bot.start))
    app.add_handler(CallbackQueryHandler(bot.handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), bot.handle_text))
    return app
