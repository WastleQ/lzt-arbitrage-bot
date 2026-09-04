# LZT Arbitrage Bot

Асинхронный Telegram-бот для автоматического поиска, оценки и перепродажи аккаунтов (**Minecraft**, **Brawl Stars**, **Valorant**) на Lolzteam Market (LZT Market).

## 🚀 Возможности

- **Мониторинг LZT API в реальном времени** — параллельный опрос категорий через `asyncio.gather`, защита от rate-limit (token bucket) и авто-ретраи с exponential backoff.
- **Интеллектуальная оценка ценности (Fair Value)** — расчёт маржи и чистой прибыли с учётом комиссий маркета, скорректированный по уверенности оценки.
- **Расширенные карточки сделок (HTML):**
  - Заголовок, цена, оценка, чистый профит, ROI.
  - **Состав лота** по категории (ранг Hypixel / BedWars ★ / плащи / кубки / гиперзаряды / ножи Valorant и т.д.).
  - **Прямая ссылка на лот LZT** + **ссылка на профиль продавца** (включая trust).
  - Все warnings (низкий trust, молодой аккаунт, чужая валюта, подозрительные слова).
- **Кнопки:** `⚡ Купить за X₽`, `🚫 В чёрный список`, `❌ Пропустить`.
- **Режимы:** Полуавтомат (уведомления) и Полный Auto-Buy с лимитами безопасности (`MAX_AUTO_BUY_PRICE`, `CONFIRM_ABOVE_PRICE`).
- **База данных SQLite** — `seen_items` (с cooldown), `trades` (история сделок), `blacklist` (чёрный список лотов), `settings_kv` (динамические настройки).
- **Telegram UI:**
  - `/start` — панель управления.
  - `/settings` — динамические пороги (FSM).
  - `/stats` — статистика за 30 дней.
  - `💰 Баланс LZT` + push-уведомления при низком балансе.
- **Безопасность:**
  - Валидация `.env` при старте (fail-fast).
  - Graceful shutdown (SIGTERM/SIGINT).
  - Кулдаун `seen_items` (`SEEN_COOLDOWN_MINUTES`).

## 🛠 Установка и запуск

1. Клонируйте репозиторий и перейдите в папку проекта.
2. Создайте виртуальное окружение и установите зависимости:
   ```bash
   python -m venv venv
   source venv/bin/activate  # или venv\Scripts\activate на Windows
   pip install -r requirements.txt
   ```
3. Скопируйте `.env.example` в `.env` и заполните:
   - `BOT_TOKEN` — токен Telegram-бота от [@BotFather](https://t.me/BotFather).
   - `ADMIN_ID` — ваш Telegram user id.
   - `LZT_API_TOKEN` — токен LZT Market (профиль → API).
4. Запустите бота:
   ```bash
   python src/main.py
   ```

## 🧪 Тесты и качество кода

```bash
pytest -q
ruff check .
ruff format --check .
```

CI запускает все три команды автоматически (`.github/workflows/ci.yml`).

## 📁 Структура

```
lzt_arbitrage_bot/
├── categories.yaml        # Веса оценщиков, пороги, множители регионов
├── .env.example           # Шаблон переменных окружения
├── requirements.txt
├── conftest.py            # pytest path setup
├── pytest.ini             # asyncio_mode=auto
├── .github/workflows/ci.yml
├── .pre-commit-config.yaml
├── src/
│   ├── __init__.py        # __version__ = "0.2.0"
│   ├── main.py            # web health-server + aiogram polling + graceful shutdown
│   ├── config.py          # Pydantic Settings + categories.yaml loader
│   ├── utils/
│   │   ├── logger.py      # loguru setup + rotation
│   │   └── rate_limiter.py # AsyncRateLimiter (token bucket)
│   ├── lzt/               # LZT Market API клиент
│   │   ├── client.py      # search_items, fast_buy, get_my_balance, rate limit, retry
│   │   └── schemas.py     # MarketItem, BuyResult
│   ├── evaluators/        # Оценка ценности по категориям
│   │   ├── base.py        # BaseEvaluator, ValuationResult
│   │   ├── minecraft.py   # Hypixel ранги, BedWars ★, плащи, full access
│   │   ├── brawlstars.py  # Кубки, гиперзаряды, Star Shelly, легендарки
│   │   └── valorant.py    # Регион (EU/NA/TR), ранги, ножи, премиум скины
│   ├── engine/arbitrage.py # Расчёт Net Profit + warnings + auto_buy_allowed
│   ├── bot/
│   │   ├── handlers.py    # /start, /settings (FSM), /stats, scanner_loop
│   │   ├── formatters.py  # deal card, buy success, stats, balance
│   │   ├── keyboards.py   # Inline-кнопки
│   │   └── states.py      # FSM: SettingsStates
│   └── db/database.py     # Database репозиторий + module-level helpers
└── tests/                 # 33 теста
    ├── test_evaluators.py
    ├── test_engine.py
    ├── test_lzt_client.py
    ├── test_database.py
    └── test_formatters.py
```

## 💸 Комиссии LZT

- Депозит: 2%
- Покупка: 0%
- Ресейл: 5%

## 📊 Логи

- stdout (цветной) + `data/bot.log` (ротация 10 MB / 7 дней, zip-сжатие).
- Уровень: `LOG_LEVEL` (по умолчанию `INFO`).

## 📜 Лицензия

Внутренний проект.
