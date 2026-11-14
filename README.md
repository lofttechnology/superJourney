# superJourney

Telegram adventure bot built with **Aiogram 3**, inline keyboards, persistent SQLite progress, an elapsed journey timer, player statistics, leaderboard, and YAML-configurable levels.

## Features

- Aiogram 3 async dispatcher and router.
- Shared elapsed timer for the entire journey; no per-level countdown or timeout.
- The active riddle card displays both total journey time and time spent on the current riddle.
- SQLite stores current level, timer start, attempts, and lifetime player statistics.
- `/stats` shows a player's results; `/leaderboard` displays the fastest completed journeys.
- Configure level text, answer options, answers, map labels, and success messages in `config/levels.yaml`.

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

Edit `config/levels.yaml`. Each level requires `title`, `question`, and `answer`. `options` controls the inline answer buttons; if the correct answer is missing, it is added automatically. Each stage can also define `map_label` and `success_message`. Existing `time_limit_seconds` values are ignored.

Commands: `/start`, `/stats`, `/leaderboard`.
