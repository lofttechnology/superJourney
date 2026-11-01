from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters

from app.domain.journey import JourneyState
from app.services.game_service import GameService


class JourneyBot:
    def __init__(self) -> None:
        self.game_service = GameService()

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        context.user_data["journey_state"] = JourneyState.POINT_1
        start_message = self.game_service.get_start_message()
        question = self.game_service.get_question_for_state(JourneyState.POINT_1)
        menu = self.game_service.build_button_menu(JourneyState.POINT_1)

        await update.message.reply_text(start_message, reply_markup=menu)
        await update.message.reply_text(
            f"🚀 {self.game_service.get_state_title(JourneyState.POINT_1)}\n\n{question}",
            reply_markup=menu,
        )

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        text = (update.message.text or "").strip()

        if text in {"/start", "🚀 Начать путешествие", "🚀 Начать заново"}:
            await self.start(update, context)
            return

        if text == "🔁 Попробовать ещё раз":
            state = context.user_data.get("journey_state", JourneyState.POINT_1)
            menu = self.game_service.build_button_menu(state)
            await update.message.reply_text(
                f"🔄 Давайте попробуем ещё раз.\n\n{self.game_service.get_question_for_state(state)}",
                reply_markup=menu,
            )
            return

        state = context.user_data.get("journey_state", JourneyState.POINT_1)
        result = self.game_service.resolve_answer(state, text)
        next_state = result["next_state"]
        context.user_data["journey_state"] = next_state

        menu = self.game_service.build_button_menu(next_state)
        await update.message.reply_text(result["message"], reply_markup=menu)

        if result["is_correct"] and next_state != JourneyState.FINISHED:
            await update.message.reply_text(
                f"🚀 {self.game_service.get_state_title(next_state)}\n\n{self.game_service.get_question_for_state(next_state)}",
                reply_markup=menu,
            )
        elif not result["is_correct"] and next_state == state:
            await update.message.reply_text(
                f"🔁 Попробуйте ещё раз.\n\n{self.game_service.get_question_for_state(state)}",
                reply_markup=menu,
            )


def build_application(token: str):
    bot = JourneyBot()
    app = ApplicationBuilder().token(token).build()
    app.add_handler(CommandHandler("start", bot.start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), bot.handle_message))
    return app
