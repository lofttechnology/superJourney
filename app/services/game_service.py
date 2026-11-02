from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from app.domain.journey import Riddle


class GameService:
    def __init__(self, repository, levels: list[Riddle]):
        self.repository = repository
        self.levels = levels

    @property
    def total_levels(self) -> int:
        return len(self.levels)

    def get_start_message(self) -> str:
        return (
            "🌍 *Добро пожаловать в superJourney!*\n\n"
            "Тебя ждут загадки, уровни и путешествие по неизведанным местам.\n"
            "⏱ На каждом уровне есть ограничение по времени.\n\n"
            "Нажми «Начать», чтобы открыть карту и отправиться в путь!"
        )

    def get_level(self, level: int) -> Riddle:
        return self.levels[level - 1]

    def get_stage_intro(self, level: int, user_id: int) -> str:
        riddle = self.get_level(level)
        remaining = self.repository.get_remaining_seconds(user_id, riddle.time_limit_seconds)
        return (
            f"🎮 *Уровень {level}/{self.total_levels}*\n"
            f"📍 {riddle.title} — {riddle.map_label}\n"
            f"⏱ Осталось: *{remaining} сек.*\n\n"
            f"{riddle.question}\n\n"
            "Выбери вариант кнопкой ниже или отправь ответ сообщением."
        )

    def build_inline_keyboard(self, level: int, page: str = "stage") -> InlineKeyboardMarkup:
        if page == "welcome":
            return InlineKeyboardMarkup([[InlineKeyboardButton("🚀 Начать путешествие", callback_data="restart")]])
        if page == "finished":
            return InlineKeyboardMarkup([
                [InlineKeyboardButton("🗺️ Финальная карта", callback_data="map")],
                [InlineKeyboardButton("🔁 Новое путешествие", callback_data="restart")],
                [InlineKeyboardButton("📊 Моя статистика", callback_data="stats")],
            ])
        if page == "map":
            return InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ К загадке", callback_data="back")],
                [InlineKeyboardButton("🔁 Начать заново", callback_data="restart")],
            ])

        riddle = self.get_level(level)
        rows = [
            [InlineKeyboardButton(f"{option}", callback_data=f"answer:{level}:{index}")]
            for index, option in enumerate(riddle.options)
        ]
        rows.extend([
            [InlineKeyboardButton("🔁 Обновить таймер", callback_data="retry"), InlineKeyboardButton("🗺️ Карта", callback_data="map")],
            [InlineKeyboardButton("📊 Статистика", callback_data="stats"), InlineKeyboardButton("🏳️ Начать заново", callback_data="restart")],
        ])
        return InlineKeyboardMarkup(rows)

    def map_text(self, current_level: int, completed: bool = False) -> str:
        path = []
        passed = self.total_levels if completed else max(0, current_level - 1)
        for index, level in enumerate(self.levels, start=1):
            marker = "✅" if index <= passed else ("📍" if index == current_level and not completed else "🔒")
            path.append(f"{marker} {level.map_label}")
        route = "\n⬇️\n".join(path)
        if completed:
            route += "\n\n🏆 *ФИНИШ — ПУТЕШЕСТВИЕ ЗАВЕРШЕНО!*"
        else:
            route += f"\n\n🎯 Текущая цель: уровень {current_level}/{self.total_levels}"
        return f"🗺️ *Карта superJourney*\n\n{route}"

    def resolve_answer(self, level: int, raw_answer: str) -> dict:
        riddle = self.get_level(level)
        if str(raw_answer).strip().casefold() == riddle.answer.strip().casefold():
            next_level = level + 1
            return {
                "is_correct": True,
                "message": riddle.success_message,
                "next_level": next_level,
                "finished": next_level > self.total_levels,
            }
        return {
            "is_correct": False,
            "message": "❌ Не совсем! Попробуй ещё раз — время ещё идёт.",
            "next_level": level,
            "finished": False,
        }

    def final_card(self, elapsed_seconds: int) -> str:
        minutes, seconds = divmod(elapsed_seconds, 60)
        route = " → ".join(level.map_label for level in self.levels)
        return (
            "🏆 *ФИНАЛЬНАЯ КАРТА ПУТЕШЕСТВИЯ*\n\n"
            "🎉 Все уровни пройдены! Ты настоящий мастер загадок.\n\n"
            f"🗺️ Маршрут:\n{route}\n\n"
            f"⏱ Время прохождения: {minutes:02d}:{seconds:02d}\n"
            f"⭐ Уровней пройдено: {self.total_levels}/{self.total_levels}\n\n"
            "Сохрани этот маршрут в памяти и отправляйся в новое приключение!"
        )

    @staticmethod
    def format_duration(seconds: int | None) -> str:
        if seconds is None:
            return "—"
        minutes, remainder = divmod(seconds, 60)
        return f"{minutes}м {remainder}с"
