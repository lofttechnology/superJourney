import asyncio
import logging

from aiogram import Bot, Dispatcher

from app.config import get_settings
from app.domain.journey import load_riddles
from app.handlers.telegram_handlers import build_router
from app.infrastructure.database import UserProgressRepository

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


async def main() -> None:
    settings = get_settings()
    levels = load_riddles(settings.levels_path)
    repository = UserProgressRepository(settings.db_path)
    journey = build_router(repository, levels)
    bot = Bot(token=settings.telegram_token)
    dispatcher = Dispatcher()
    dispatcher.include_router(journey.router)
    dispatcher.shutdown.register(journey.shutdown)

    logging.info("Starting superJourney with Aiogram and %s configured levels...", len(levels))
    try:
        await dispatcher.start_polling(bot)
    finally:
        await bot.session.close()


def run() -> None:
    asyncio.run(main())


if __name__ == "__main__":
    run()
