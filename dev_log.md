# Журнал разработки (dev_log.md)

## [2026-09-04] Масштабная доработка LZT Arbitrage Bot (v0.2.0)

### Безопасность и стабильность
* **Rate limiter (token bucket)** в `src/utils/rate_limiter.py` — защита от 429 на LZT API.
* **Ретраи с exponential backoff** в `LZTClient._request` — 4 попытки с `Retry-After` header.
* **Graceful shutdown** в `src/main.py` — обработка SIGTERM/SIGINT, отмена polling, закрытие сессий.
* **Валидация .env при старте** — fail-fast с понятным сообщением при placeholder-токенах.
* **Кулдаун seen_items** — `SEEN_COOLDOWN_MINUTES` (по умолчанию 30) не показывает лот повторно.
* **Чёрный список лотов** — таблица `blacklist` + кнопка «🚫 В чёрный список» в карточке.
* **Auto-Buy safety** — `MAX_AUTO_BUY_PRICE` (жёсткий лимит) и `CONFIRM_ABOVE_PRICE` (требует подтверждения).
* **`min_balance_alert`** — push-уведомление админу при балансе LZT ниже порога.

### Функциональность
* **`/stats`** — статистика за 30 дней: сделок, потрачено, профит, разбивка по статусам/категориям.
* **Параллельный парсинг категорий** через `asyncio.gather` (раньше — последовательно).
* **Health-мониторинг API** — `last_api_failure` + balance monitor в фоне.
* **Динамические пороги через FSM** — `/settings` → inline-кнопки «Min Profit / Min ROI / Cooldown / Auto-Buy», состояния сохраняются в `settings_kv`.
* **Адаптивный min_roi** — `engine.adaptive_min_roi()` калибрует порог по realized ROI из trades.

### Расширенная карточка сделки (HTML)
* Заголовок с категорией, полное название лота.
* Цена, оценка, комиссия ресейла, чистый профит, ROI + скорректированный ROI с учётом уверенности.
* «Состав лота» — парсинг по категориям:
  * **Minecraft**: ранг Hypixel, BedWars ★, плащи (Minecon/Migrator/OptiFine), full access.
  * **Brawl Stars**: кубки, гиперзаряды, Star Shelly, Mecha, легендарки.
  * **Valorant**: регион, ранг, ножи, премиум скины, всего скинов.
* Профиль продавца (trust), **ссылка на лот**, **ссылка на профиль продавца**.
* Все warnings (низкий trust, молодой аккаунт, подозрительные слова, неизвестный возраст, чужая валюта, низкая уверенность).
* Кнопка «⚡ Купить за X₽» (цена в тексте), «🚫 В чёрный список», «❌ Пропустить».
* **Карточка покупки** — `format_buy_success` выводит полученные данные аккаунта (логин/пароль/почта).

### Архитектура и качество
* **categories.yaml** — веса оценщиков, пороги, множители регионов — всё в одном файле, перегрузка через Pydantic.
* **`src/db/database.py`** рефакторен: класс `Database` (репозиторий), плюс module-level алиасы. Добавлены `blacklist` и `settings_kv`.
* **Loguru** вместо print: stdout + ротация в `data/bot.log` (10 MB / 7 days), перехват stdlib logging.
* **Типизация и docstrings** — все аргументы, returns, type hints.
* **Версионирование** — `__version__ = "0.2.0"` в `src/__init__.py`, пробрасывается в `User-Agent` и `/healthz`.

### Тесты (33/33 ✅)
* `tests/test_evaluators.py` — 9 тестов (Minecraft, Brawl Stars, Valorant, banned/cape/full access/TR penalty).
* `tests/test_engine.py` — 10 тестов (warnings, profit/ROI, currency, auto-buy gates, low profit skip).
* `tests/test_lzt_client.py` — 4 теста с FakeSession (balance, retry 429, search, fast_buy error).
* `tests/test_database.py` — 6 тестов с временной БД (seen cooldown, blacklist, trades, stats, kv).
* `tests/test_formatters.py` — 4 теста (deal card, warnings, balance, stats, FSM).

### CI / DX
* `.github/workflows/ci.yml` — lint (ruff check) + format check (ruff format --check) + pytest на каждый PR.
* `.pre-commit-config.yaml` — ruff + ruff-format.
* `conftest.py` — `sys.path` для pytest 9.x, который игнорирует `pythonpath` в ini.

## [2026-09-04] Система предупреждений и безопасность (v0.1.0)
* Warnings (низкий trust, молодой аккаунт, exclude_words) в `engine/arbitrage.py`.
* Карточки сделок в `bot/handlers.py` отображают warnings.
* Настройки `min_seller_trust`, `min_account_age_days`, `exclude_words` в `config.py`.
* 3 модульных теста на warnings.
