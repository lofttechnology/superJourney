# superJourney

Telegram adventure bot with inline keyboards, persistent SQLite progress, real-time countdown, player statistics, leaderboard and YAML-configurable levels.

## Features

- Live level countdown (updates every second using Telegram job queue).
- SQLite stores current level, timer start, attempts, timeouts and lifetime player statistics.
- `/stats` shows a player's lifetime results.
- `/leaderboard` displays the fastest completed journeys.
- Edit levels, options, answers and per-level time limits in `config/levels.yaml`.
- Existing progress database is migrated automatically with additive columns.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# set TELEGRAM_TOKEN in .env
python -m app.main
```

Optional `.env` settings: `DB_PATH` and `LEVELS_PATH`.

## Configure levels

Edit `config/levels.yaml`. Each level requires `title`, `question`, and `answer`. `options` controls the inline answer buttons; if the correct answer is missing, it is added automatically. Each stage can have its own `time_limit_seconds`, `map_label`, and `success_message`.

Example:

```yaml
levels:
  - id: forest
    title: "Точка 1"
    map_label: "🌿 Лесная тропа"
    question: "Сколько будет 2 + 3?"
    answer: "5"
    options: ["3", "5", "8"]
    time_limit_seconds: 30
    success_message: "Верно!"
```

Commands: `/start`, `/stats`, `/leaderboard`.
