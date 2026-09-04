import asyncio
import os
import sys

from aiohttp import web

from src.bot.handlers import bot, dp, lzt_client
from src.config import settings
from src.db.database import init_db
from src.utils.logger import logger, setup_logging


async def handle_health(request: web.Request) -> web.Response:
    return web.json_response(
        {
            "status": "ok",
            "service": "lzt-arbitrage-bot",
            "version": settings.version,
        }
    )


async def start_web_server() -> web.AppRunner:
    app = web.Application()
    app.router.add_get("/", handle_health)
    app.router.add_get("/healthz", handle_health)

    port = int(os.environ.get("PORT", "10000"))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info(f"Web server started on port {port}")
    return runner


def _validate_env() -> None:
    placeholders = ("test_", "your_", "changeme", "1234567890")
    if any(settings.bot_token.lower().startswith(p) for p in placeholders):
        logger.error("BOT_TOKEN looks like a placeholder. Set real value in .env")
        sys.exit(1)
    if any(settings.lzt_api_token.lower().startswith(p) for p in placeholders):
        logger.error("LZT_API_TOKEN looks like a placeholder. Set real value in .env")
        sys.exit(1)
    if settings.admin_id == 123456:
        logger.error("ADMIN_ID is still default. Set real Telegram user id in .env")
        sys.exit(1)


async def main() -> None:
    setup_logging()
    _validate_env()

    logger.info(f"LZT Arbitrage Bot v{settings.version} starting...")
    await init_db()

    runner = await start_web_server()
    shutdown_event = asyncio.Event()

    loop = asyncio.get_running_loop()
    for sig in (
        asyncio.unix_events.SignalType.SIGTERM,
        asyncio.unix_events.SignalType.SIGINT,
    ):
        try:
            loop.add_signal_handler(sig, shutdown_event.set)
        except (NotImplementedError, RuntimeError):
            pass

    polling_task = asyncio.create_task(dp.start_polling(bot, handle_signals=False))
    wait_shutdown = asyncio.create_task(shutdown_event.wait())

    _done, pending = await asyncio.wait(
        {polling_task, wait_shutdown},
        return_when=asyncio.FIRST_COMPLETED,
    )

    logger.info("Shutting down gracefully...")
    for task in pending:
        task.cancel()
    for task in pending:
        try:
            await task
        except asyncio.CancelledError:
            pass
        except (OSError, RuntimeError) as exc:
            logger.warning(f"Shutdown cleanup error: {exc}")

    await lzt_client.close()
    await runner.cleanup()
    await bot.session.close()
    logger.info("Bot stopped.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped.")
