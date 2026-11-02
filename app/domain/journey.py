from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class Riddle:
    title: str
    question: str
    answer: str
    success_message: str
    map_label: str
    options: tuple[str, ...]
    time_limit_seconds: int


def load_riddles(path: str | Path) -> list[Riddle]:
    """Load and validate level definitions from YAML."""
    config_path = Path(path)
    try:
        raw: Any = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RuntimeError(f"Levels configuration not found: {config_path}") from exc
    except yaml.YAMLError as exc:
        raise RuntimeError(f"Invalid YAML in levels configuration: {exc}") from exc

    if not isinstance(raw, dict) or not isinstance(raw.get("levels"), list) or not raw["levels"]:
        raise RuntimeError("Levels YAML must contain a non-empty 'levels' list.")

    levels: list[Riddle] = []
    seen_ids: set[str] = set()
    for index, item in enumerate(raw["levels"], start=1):
        if not isinstance(item, dict):
            raise RuntimeError(f"Level {index} must be a mapping.")
        level_id = str(item.get("id", index))
        if level_id in seen_ids:
            raise RuntimeError(f"Duplicate level id: {level_id}")
        seen_ids.add(level_id)

        title = _required_string(item, "title", index)
        question = _required_string(item, "question", index)
        answer = str(item.get("answer", "")).strip()
        if not answer:
            raise RuntimeError(f"Level {index} must define a non-empty answer.")
        options_raw = item.get("options", [answer])
        if not isinstance(options_raw, list) or not options_raw:
            raise RuntimeError(f"Level {index} options must be a non-empty list.")
        options = tuple(dict.fromkeys(str(option).strip() for option in options_raw))
        if answer not in options:
            options = (*options, answer)
        if any(not option for option in options):
            raise RuntimeError(f"Level {index} options cannot be empty.")
        time_limit = item.get("time_limit_seconds", 30)
        if not isinstance(time_limit, int) or time_limit < 1:
            raise RuntimeError(f"Level {index} time_limit_seconds must be a positive integer.")

        levels.append(
            Riddle(
                title=title,
                question=question,
                answer=answer,
                success_message=str(item.get("success_message", "✅ Верно! Уровень пройден.")),
                map_label=str(item.get("map_label", f"📍 {title}")),
                options=options,
                time_limit_seconds=time_limit,
            )
        )
    return levels


def _required_string(item: dict[str, Any], key: str, index: int) -> str:
    value = item.get(key)
    if not isinstance(value, str) or not value.strip():
        raise RuntimeError(f"Level {index} must define a non-empty '{key}'.")
    return value.strip()
