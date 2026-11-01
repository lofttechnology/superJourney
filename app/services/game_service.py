from datetime import datetime, timezone

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from app.domain.journey import JourneyState, MAX_TIME_PER_STAGE, RIDDLES, TOTAL_LEVELS


class GameService:
    def __init__(self, repository):
        self.repository = repository

    def get_level_number(self, state: JourneyState) -> int:
        if state == JourneyState.POINT_1:
            return 1
        if state == JourneyState.POINT_2:
            return 2
        if state == JourneyState.POINT_3:
            return 3
        return TOTAL_LEVELS

    def get_start_message(self) -> str:
        return (
            "🌍 Добро пожаловать в superJourney!\n\n"
            "Ты отправляешься в увлекательное путешествие по трем таинственным точкам.\n"
            "Каждая точка скрывает свою загадку, а правильный ответ открывает следующий этап.\n\n"
            "🧭 Цель: пройти все три уровня и добраться до финальной точки."
        )

    def get_status_line(self, state: JourneyState, user_id: int) -> str:
        level = self.get_level_number(state)
        remaining = self.repository.get_remaining_seconds(user_id, MAX_TIME_PER_STAGE)
        title = RIDDLES.get(state).title if state in RIDDLES else "Финальная точка"
        return (
            f"🎮 Уровень: {level}/{TOTAL_LEVELS} | "
            f"📍 {title} | "
            f"⏱ Таймер: {remaining}s"
        )

    def get_question_for_state(self, state: JourneyState) -> str:
        riddle = RIDDLES.get(state)
        if riddle is None:
            return "🏁 Путешествие завершено! Вы уже прошли все уровни.\n\n🗺️ Карта путешествия:\n🌿 Лесная тропа → 🏔️ Горный перевал → 🏆 Финальная башня"
        return riddle.question

    def get_state_title(self, state: JourneyState) -> str:
        riddle = RIDDLES.get(state)
        if riddle is None:
            return "Финальная точка"
        return riddle.title

    def get_map_text(self) -> str:
        return (
            "🗺️ Карта путешествия\n\n"
            "🌿 Лесная тропа → 🏔️ Горный перевал → 🏆 Финальная башня\n\n"
            "✅ Пройдено: 0/3\n"
            "🎯 Следующая цель: открыть финальную точку."
        )

    def build_inline_keyboard(self, state: JourneyState):
        if state == JourneyState.FINISHED:
            return InlineKeyboardMarkup(
                [
                    [InlineKeyboardButton("🔁 Начать заново", callback_data="restart")],
                    [InlineKeyboardButton("🗺️ Показать карту", callback_data="map")],
                ]
            )

        riddle = RIDDLES[state]
        return InlineKeyboardMarkup(
            [
                [InlineKeyboardButton(f"✅ Ответ: {riddle.answer}", callback_data=f"answer:{riddle.answer}")],
                [
                    InlineKeyboardButton("🔁 Попробовать снова", callback_data="retry"),
                    InlineKeyboardButton("🗺️ Карта", callback_data="map"),
                ],
                [InlineKeyboardButton("🚀 Сбросить игру", callback_data="restart")],
            ]
        )

    def resolve_answer(self, state: JourneyState, raw_answer: str):
        riddle = RIDDLES.get(state)
        if riddle is None:
            return {
                "is_correct": False,
                "message": "🏁 Путешествие завершено.",
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

    def build_final_victory(self) -> str:
        return (
            "🎉 Поздравляем!\n\n"
            "Вы прошли все три уровня и успешно завершили путешествие.\n\n"
            "🏆 Итог: путь пройден, таймер побеждён, карта открыта.\n"
            "Вы настоящий путешественник!"
        )

    def get_stage_intro(self, state: JourneyState, user_id: int) -> str:
        status = self.get_status_line(state, user_id)
        question = self.get_question_for_state(state)
        return f"{status}\n\n{question}"
