from dataclasses import dataclass
from enum import IntEnum


MAX_TIME_PER_STAGE = 30
TOTAL_LEVELS = 3


class JourneyState(IntEnum):
    START = 0
    POINT_1 = 1
    POINT_2 = 2
    POINT_3 = 3
    FINISHED = 4


@dataclass(frozen=True)
class Riddle:
    title: str
    question: str
    answer: int
    success_message: str
    map_label: str


POINT_1 = Riddle(
    title="Точка 1",
    question="🧩 Загадка 1\nСколько будет: 2 + 3?",
    answer=5,
    success_message="✅ Верно! Это число 5. Вы открыли первую точку путешествия. Переходим к точке 2!",
    map_label="🌿 Лесная тропа",
)

POINT_2 = Riddle(
    title="Точка 2",
    question="🧩 Загадка 2\nСколько будет: 3 × 7?",
    answer=21,
    success_message="✅ Отлично! Ответ 21 — верный. Вы справились со второй точкой. Переходим к точке 3.",
    map_label="🏔️ Горный перевал",
)

POINT_3 = Riddle(
    title="Точка 3",
    question="🧩 Загадка 3\nСколько будет: 14 ÷ 2?",
    answer=7,
    success_message="✅ Поздравляем! Ответ 7 — правильный. Вы завершили путешествие и прошли финальную точку!",
    map_label="🏆 Финальная башня",
)

RIDDLES = {
    JourneyState.POINT_1: POINT_1,
    JourneyState.POINT_2: POINT_2,
    JourneyState.POINT_3: POINT_3,
}
