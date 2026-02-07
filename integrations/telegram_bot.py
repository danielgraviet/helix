"""
Helix Telegram Bot

Standalone: python -m integrations.telegram_bot
Background: called via TelegramManager from the CLI
"""
from dotenv import load_dotenv
load_dotenv()

import asyncio  # noqa: E402
import logging  # noqa: E402
import threading  # noqa: E402

from telegram import Update  # noqa: E402
from telegram.ext import (  # noqa: E402
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

import config  # noqa: E402
from orchestrator.agent import run_agent  # noqa: E402
from orchestrator.registry import SkillRegistry  # noqa: E402
from skill_factory.factory import remove_skill  # noqa: E402

logger = logging.getLogger(__name__)


# --- Handler factories (close over the shared registry) ---

def _make_start_handler():
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await update.message.reply_text(
            "Helix — Skills that evolve on demand.\n\n"
            "Send me a task and I'll create microservice skills to solve it.\n\n"
            "Commands:\n"
            "/skills — list active skills\n"
            "/clear — remove all skills and containers"
        )
    return handler


def _make_skills_handler(registry: SkillRegistry):
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        skills = registry.list_skills()
        if not skills:
            await update.message.reply_text("No skills registered yet.")
            return
        lines = []
        for s in skills:
            lines.append(f"- {s['name']}: {s['description']} ({s['status']})")
        await update.message.reply_text("\n".join(lines))
    return handler


def _make_clear_handler(registry: SkillRegistry):
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        skills = registry.list_skills()
        if not skills:
            await update.message.reply_text("Nothing to clean up.")
            return
        count = len(skills)
        for skill_info in skills:
            skill = registry.lookup(skill_info["name"])
            if skill:
                try:
                    remove_skill(skill)
                except Exception:
                    pass
        await update.message.reply_text(f"Removed {count} skill(s).")
    return handler


def _make_message_handler(registry: SkillRegistry):
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user_text = update.message.text
        thinking_msg = await update.message.reply_text("Working on it... (this may take a minute)")

        try:
            response = await asyncio.to_thread(run_agent, user_text, registry)

            if len(response) <= 4096:
                await update.message.reply_text(response)
            else:
                for i in range(0, len(response), 4096):
                    await update.message.reply_text(response[i:i + 4096])
        except Exception as e:
            await update.message.reply_text(f"Error: {e}")
        finally:
            try:
                await thinking_msg.delete()
            except Exception:
                pass
    return handler


# --- Bot lifecycle ---

async def _run_bot_async(registry: SkillRegistry, stop_event: threading.Event) -> None:
    """Build the Telegram app, start polling, wait for stop signal, shut down."""
    app = ApplicationBuilder().token(config.TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", _make_start_handler()))
    app.add_handler(CommandHandler("skills", _make_skills_handler(registry)))
    app.add_handler(CommandHandler("clear", _make_clear_handler(registry)))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, _make_message_handler(registry)))

    await app.initialize()
    await app.updater.start_polling()
    await app.start()
    logger.info("Helix Telegram bot started (polling mode).")

    while not stop_event.is_set():
        await asyncio.sleep(0.5)

    logger.info("Telegram bot shutting down...")
    await app.updater.stop()
    await app.stop()
    await app.shutdown()
    logger.info("Telegram bot stopped.")


def start_bot(registry: SkillRegistry, stop_event: threading.Event) -> None:
    """Run the Telegram bot in the current thread (blocking).

    Call from a background thread. Set stop_event to trigger shutdown.
    """
    if not config.TELEGRAM_BOT_TOKEN:
        logger.error(
            "TELEGRAM_BOT_TOKEN not set. "
            "Add it to your .env file. "
            "Get a token from @BotFather on Telegram."
        )
        return

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_run_bot_async(registry, stop_event))
    finally:
        loop.close()


# --- Standalone mode ---

if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO,
    )
    _standalone_registry = SkillRegistry()
    _stop = threading.Event()
    try:
        start_bot(_standalone_registry, _stop)
    except KeyboardInterrupt:
        _stop.set()
