"""Standalone Telegram HTML Widget (HTML Bubble) demo bot.

Run with ``python -m app.widget_demo``. This entry point is separate from
``app.main`` so the existing adventure bot remains unchanged.
"""

import asyncio
import logging

from aiogram import Bot, Dispatcher, Router
from aiogram.filters import Command
from aiogram.methods.base import TelegramMethod
from aiogram.types import Message

from app.config import get_settings
from app.widgets.html_bubble import HTML_BUBBLE

logger = logging.getLogger(__name__)


class SendWidget(TelegramMethod[Message]):
    """Bot API sendWidget method, for Aiogram versions without a generated wrapper."""

    __returning__ = Message
    __api_method__ = "sendWidget"

    chat_id: int
    widget: dict[str, str]


router = Router(name="html-widget-demo")


@router.message(Command("start"))
async def start(message: Message) -> None:
    await message.answer(
        "Привет! Это отдельный тестовый бот для HTML Widgets / HTML Bubbles.\n\n"
        "Команда /widget отправит интерактивную HTML-карточку: попробуйте менять "
        "тему, отмечать пункты и нажимать кнопки прямо внутри виджета."
    )


@router.message(Command("widget"))
async def send_widget(message: Message, bot: Bot) -> None:
    if message.chat.type != "private":
        await message.answer("Демо HTML Widgets предназначено для личного чата с ботом.")
        return

    try:
        await bot(
            SendWidget(
                chat_id=message.chat.id,
                widget={"html": HTML_BUBBLE},
            )
        )
    except Exception:
        logger.exception("Telegram sendWidget request failed")
        await message.answer(
            "Не удалось отправить HTML-виджет. Проверьте, что токен принадлежит "
            "боту с поддержкой актуального Telegram Bot API и что HTML Widgets "
            "доступны для этого бота. Подробности ошибки записаны в лог."
        )


async def main() -> None:
    settings = get_settings()
    bot = Bot(token=settings.telegram_token)
    dispatcher = Dispatcher()
    dispatcher.include_router(router)
    logger.info("Starting standalone HTML Widget demo bot")
    try:
        await dispatcher.start_polling(bot)
    finally:
        await bot.session.close()


def run() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    asyncio.run(main())


if __name__ == "__main__":
    run()
