import logging

from app.config import get_settings
from app.handlers.telegram_handlers import build_application

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def main() -> None:
    settings = get_settings()
    app = build_application(settings.telegram_token)
    logging.info("Starting superJourney bot...")
    app.run_polling()


if __name__ == "__main__":
    main()
