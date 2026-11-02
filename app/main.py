import logging

from app.config import get_settings
from app.domain.journey import load_riddles
from app.handlers.telegram_handlers import build_application

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def main() -> None:
    settings = get_settings()
    levels = load_riddles(settings.levels_path)
    app = build_application(settings.telegram_token, settings.db_path, levels)
    logging.info("Starting superJourney bot with %s configured levels...", len(levels))
    app.run_polling()


if __name__ == "__main__":
    main()
