from dataclasses import dataclass
from os import getenv

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    telegram_token: str
    db_path: str = "data/superjourney.db"


def get_settings() -> Settings:
    token = getenv("TELEGRAM_TOKEN")
    if not token:
        raise RuntimeError("TELEGRAM_TOKEN is not set. Add it to your .env file.")
    db_path = getenv("DB_PATH", "data/superjourney.db")
    return Settings(telegram_token=token, db_path=db_path)
