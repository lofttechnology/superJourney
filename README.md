# superJourney

Telegram-бот путешествия по точкам с красивым интерфейсом через кнопки и меню Telegram.

## Функционал

- `/start` запускает путешествие
- Точка 1: ответ `5`
- Точка 2: ответ `21`
- Точка 3: ответ `7`
- Неверный ответ — предлагает повторить попытку
- Правильный ответ — переход к следующей точке
- Кнопки Telegram для удобного ввода ответа

## Архитектура

Проект разделён на слои:

- `app/domain` — сущности и сценарий путешествия
- `app/services` — логика проверки ответов и сценария
- `app/handlers` — обработчики Telegram и клавиатура
- `app/config.py` — чтение `.env`
- `app/main.py` — точка входа

## Запуск

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# вставьте токен Telegram-бота в .env
python -m app.main
```
