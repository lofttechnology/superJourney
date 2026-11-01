from telegram import ReplyKeyboardMarkup

from app.domain.journey import JourneyState, RIDDLES


class GameService:
    def get_start_message(self) -> str:
        return (
            "🌍 Добро пожаловать в superJourney!\n\n"
            "Ты отправляешься в путешествие по трем таинственным точкам.\n"
            "Нажми кнопку ниже, чтобы начать."
        )

    def get_question_for_state(self, state: JourneyState) -> str:
        riddle = RIDDLES.get(state)
        if riddle is None:
            return "🏁 Путешествие завершено. Можно начать заново."
        return riddle.question

    def get_state_title(self, state: JourneyState) -> str:
        riddle = RIDDLES.get(state)
        if riddle is None:
            return "Финальная точка"
        return riddle.title

    def build_button_menu(self, state: JourneyState):
        if state == JourneyState.FINISHED:
            return ReplyKeyboardMarkup([["🚀 Начать заново"]], resize_keyboard=True)

        answer = str(RIDDLES[state].answer)
        return ReplyKeyboardMarkup(
            [[answer], ["🔁 Попробовать ещё раз"], ["🚀 Начать заново"]],
            resize_keyboard=True,
        )

    def resolve_answer(self, state: JourneyState, raw_answer: str):
        riddle = RIDDLES.get(state)
        if riddle is None:
            return {
                "is_correct": False,
                "message": "🏁 Путешествие уже завершено.",
                "next_state": JourneyState.FINISHED,
            }

        normalized = (raw_answer or "").strip()
        if not normalized:
            return {
                "is_correct": False,
                "message": "⚠️ Пожалуйста, пришлите число.",
                "next_state": state,
            }

        try:
            answer = int(normalized)
        except ValueError:
            return {
                "is_correct": False,
                "message": "⚠️ Ответ должен быть числом. Попробуйте ещё раз.",
                "next_state": state,
            }

        if answer == riddle.answer:
            if state == JourneyState.POINT_1:
                return {
                    "is_correct": True,
                    "message": riddle.success_message,
                    "next_state": JourneyState.POINT_2,
                }
            if state == JourneyState.POINT_2:
                return {
                    "is_correct": True,
                    "message": riddle.success_message,
                    "next_state": JourneyState.POINT_3,
                }
            if state == JourneyState.POINT_3:
                return {
                    "is_correct": True,
                    "message": riddle.success_message,
                    "next_state": JourneyState.FINISHED,
                }

        return {
            "is_correct": False,
            "message": "❌ Неверный ответ. Попробуйте ещё раз.",
            "next_state": state,
        }
