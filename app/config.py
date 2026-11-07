from dataclasses import dataclass
from pathlib import Path
from os import getenv

from dotenv import load_dotenv


# Resolve configuration from the repository root, not the IDE's working directory.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")


def _project_path(value: str) -> Path:
    path = Path(value).expanduser()
    return path if path.is_absolute() else PROJECT_ROOT / path


@dataclass(frozen=True)
class Settings:
    telegram_token: str
    db_path: Path
    levels_path: Path


def get_settings() -> Settings:
    token = getenv("TELEGRAM_TOKEN")
    if not token:
        raise RuntimeError(
            f"TELEGRAM_TOKEN is not set. Add it to {PROJECT_ROOT / '.env'} "
            "(copy .env.example first)."
        )
    return Settings(
        telegram_token=token,
        db_path=_project_path(getenv("DB_PATH", "data/superjourney.db")),
        levels_path=_project_path(getenv("LEVELS_PATH", "config/levels.yaml")),
    )
