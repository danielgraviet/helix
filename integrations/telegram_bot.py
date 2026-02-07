"""
Helix Telegram Bot — run as: python -m integrations.telegram_bot
"""
from dotenv import load_dotenv
load_dotenv()

import asyncio  # noqa: E402
import logging  # noqa: E402

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

registry = SkillRegistry()


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Helix — Skills that evolve on demand.\n\n"
        "Send me a task and I'll create microservice skills to solve it.\n\n"
        "Commands:\n"
        "/skills — list active skills\n"
        "/clear — remove all skills and containers"
    )


async def skills_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    skills = registry.list_skills()
    if not skills:
        await update.message.reply_text("No skills registered yet.")
        return
    lines = []
    for s in skills:
        lines.append(f"- {s['name']}: {s['description']} ({s['status']})")
    await update.message.reply_text("\n".join(lines))


async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_text = update.message.text

    thinking_msg = await update.message.reply_text("Working on it... (this may take a minute)")

    try:
        response = await asyncio.to_thread(run_agent, user_text, registry)

        # Telegram messages have a 4096 char limit
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


async def post_shutdown(application) -> None:
    """Clean up Docker containers when the bot shuts down."""
    skills = registry.list_skills()
    for skill_info in skills:
        skill = registry.lookup(skill_info["name"])
        if skill:
            try:
                remove_skill(skill)
            except Exception:
                pass


def main() -> None:
    if not config.TELEGRAM_BOT_TOKEN:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN not set. "
            "Add it to your .env file. "
            "Get a token from @BotFather on Telegram."
        )

    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO,
    )

    app = ApplicationBuilder().token(config.TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("skills", skills_command))
    app.add_handler(CommandHandler("clear", clear_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app.post_shutdown = post_shutdown

    logger.info("Helix Telegram bot starting (polling mode)...")
    app.run_polling()


if __name__ == "__main__":
    main()