# superJourney

Telegram adventure bot built with **Aiogram 3**, inline keyboards, persistent SQLite progress, a live countdown, player statistics, leaderboard, and YAML-configurable levels.

## Features

- Aiogram 3 async dispatcher and router.
- Live level countdown (the level message is updated once per second).
- SQLite stores current level, timer start, attempts, timeouts, and lifetime player statistics.
- `/stats` shows a player's results; `/leaderboard` displays the fastest completed journeys.
- Configure level text, answer options, answers, map labels, success messages, and time limits in `config/levels.yaml`.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env .env
# set TELEGRAM_TOKEN in .env
python -m app.main
```

Optional `.env` settings: `DB_PATH` and `LEVELS_PATH`.

## Configure levels

Edit `config/levels.yaml`. Each level requires `title`, `question`, and `answer`. `options` controls the inline answer buttons; if the correct answer is missing, it is added automatically. Each stage can have its own `time_limit_seconds`, `map_label`, and `success_message`.

Commands: `/start`, `/stats`, `/leaderboard`.
