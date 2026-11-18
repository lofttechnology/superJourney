# HTML Widgets (HTML Bubbles) demo

This repository includes a small, standalone Telegram bot for trying the Bot API's HTML Widget feature. It uses the same Python dependencies as the adventure bot (`aiogram==3.13.1`, `python-dotenv==1.0.1`, and `PyYAML==6.0.2`). No additional package is required. The demo lives alongside the existing bot and does not change its `/start` behavior.

## Run the demo

1. Create a bot with [@BotFather](https://t.me/BotFather) and put its token in the existing `.env` file as `TELEGRAM_TOKEN=...` (copy `.env.example` if needed).
2. Install dependencies as described in `README.md`.
3. Run this separate bot process:

   ```bash
   python -m app.widget_demo
   ```

4. Open a private chat with that bot, send `/start`, then `/widget`.

The widget is a self-contained HTML document with inline CSS and JavaScript. It demonstrates a checklist, updating UI state, and changing the accent color without loading remote assets or making network requests. The bot uses Aiogram's `TelegramMethod` interface to call `sendWidget`, which is not present as a generated method in the repository's pinned Aiogram 3.13.1. The adventure bot remains available through its existing `python -m app.main` entry point; do not run both processes against the same bot token at once.

## API availability

`sendWidget` requires a Telegram Bot API server that supports HTML Widgets and a bot/account for which Telegram has enabled the feature. If the server responds that the method is unknown or unavailable, this is a Bot API availability/eligibility issue, not a widget rendering failure. The bot logs the API error for diagnosis. See the [Telegram Bot API documentation](https://core.telegram.org/bots/api) and [HTML Widgets guide](https://core.telegram.org/bots/widgets) for current eligibility and payload requirements.
