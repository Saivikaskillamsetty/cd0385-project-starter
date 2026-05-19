"""
Telegram bot interface for content-to-tasks-bot.

Flow:
  User sends URL  -> bot fetches content -> Claude extracts tasks -> Notion pages created
  User sends text -> Claude extracts tasks -> Notion pages created
  Manual fallback -> bot asks user to paste content -> then processes it
"""

import logging
import os
import re

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from bot.analyzer import analyze_content
from bot.fetchers import get_fetcher
from bot.models import ExtractedTask, FetchedContent
from bot.notion_writer import create_tasks_batch

load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

URL_PATTERN = re.compile(r"https?://\S+")

WAITING_FOR_MANUAL_CONTENT = 1


# ── formatting helpers ────────────────────────────────────────────────────────

def _format_tasks(tasks: list[ExtractedTask], notion_urls: list[str]) -> str:
    lines = [f"Extracted {len(tasks)} task(s):\n"]
    for i, (task, nurl) in enumerate(zip(tasks, notion_urls or [""] * len(tasks)), 1):
        cats = ", ".join(task.categories) if task.categories else "General"
        lines.append(
            f"{i}. [{task.priority}] {task.title}\n"
            f"   {task.description}\n"
            f"   Effort: {task.effort} | {cats}"
        )
        if nurl:
            lines.append(f"   Notion: {nurl}")
    return "\n\n".join(lines)


# ── shared processing logic ───────────────────────────────────────────────────

async def _run_pipeline(
    content: FetchedContent,
    status_msg,
) -> str:
    await status_msg.edit_text("Analyzing with Claude...")

    tasks = analyze_content(content)

    notion_token = os.environ.get("NOTION_API_TOKEN", "")
    db_id = os.environ.get("NOTION_DATABASE_ID", "")
    notion_urls: list[str] = []

    if notion_token and db_id:
        await status_msg.edit_text(f"Creating {len(tasks)} task(s) in Notion...")
        notion_urls = create_tasks_batch(db_id, tasks, notion_token)
    else:
        logger.warning("Notion env vars not set — skipping Notion write")

    result = _format_tasks(tasks, notion_urls)
    if not (notion_token and db_id):
        result += "\n\n(Notion write skipped — set NOTION_API_TOKEN and NOTION_DATABASE_ID to enable)"

    return result


# ── command handlers ──────────────────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Content-to-Tasks Bot\n\n"
        "Send me a URL or paste any text and I will extract actionable tasks into Notion.\n\n"
        "Supported:\n"
        "  - Articles and blog posts\n"
        "  - YouTube videos\n"
        "  - Tweets / X posts\n"
        "  - Instagram reels (paste caption if auto-fetch fails)\n"
        "  - Plain text or notes\n\n"
        "/help for usage tips"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "How to use:\n\n"
        "1. Send a URL — I fetch the page and extract tasks.\n"
        "2. Send plain text — I treat it as content and extract tasks.\n"
        "3. For Instagram/Twitter I cannot scrape, I will ask you to paste the text.\n\n"
        "Tasks are saved to your Notion database automatically.\n\n"
        "Required env vars: ANTHROPIC_API_KEY, NOTION_API_TOKEN, NOTION_DATABASE_ID, TELEGRAM_BOT_TOKEN"
    )


# ── URL handler ───────────────────────────────────────────────────────────────

async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    url = URL_PATTERN.search(update.message.text).group(0)
    status_msg = await update.message.reply_text("Fetching content...")

    try:
        fetcher = get_fetcher(url)
        content = fetcher.fetch(url)
    except Exception as e:
        logger.exception("Fetch error for %s", url)
        await status_msg.edit_text(
            f"Could not fetch that URL ({e}).\n\nTry pasting the content as text instead."
        )
        return ConversationHandler.END

    if content.fetch_method == "manual_fallback":
        context.user_data["pending_url"] = url
        context.user_data["pending_source_type"] = content.source_type
        await status_msg.edit_text(
            f"I cannot auto-fetch {content.source_type} content.\n\n"
            "Please paste the caption or description from the post:"
        )
        return WAITING_FOR_MANUAL_CONTENT

    try:
        result = await _run_pipeline(content, status_msg)
        await status_msg.edit_text(result)
    except Exception as e:
        logger.exception("Pipeline error")
        await status_msg.edit_text(f"Something went wrong: {e}")

    return ConversationHandler.END


# ── manual content handler (called after fallback prompt) ─────────────────────

async def handle_manual_content(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    pasted = update.message.text.strip()
    url = context.user_data.get("pending_url", "unknown")
    source_type = context.user_data.get("pending_source_type", "article")

    if not pasted:
        await update.message.reply_text("No content received. Send the URL again to retry.")
        return ConversationHandler.END

    content = FetchedContent(
        url=url,
        source_type=source_type,
        title=f"{source_type.capitalize()} post",
        body=pasted,
        fetch_method="manual_fallback",
    )

    status_msg = await update.message.reply_text("Processing pasted content...")
    try:
        result = await _run_pipeline(content, status_msg)
        await status_msg.edit_text(result)
    except Exception as e:
        logger.exception("Pipeline error on manual content")
        await status_msg.edit_text(f"Something went wrong: {e}")

    return ConversationHandler.END


# ── plain text handler ────────────────────────────────────────────────────────

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text.strip()
    if not text:
        return

    content = FetchedContent(
        url="direct-input",
        source_type="text",
        title="User-submitted content",
        body=text,
        fetch_method="direct",
    )

    status_msg = await update.message.reply_text("Analyzing your text...")
    try:
        result = await _run_pipeline(content, status_msg)
        await status_msg.edit_text(result)
    except Exception as e:
        logger.exception("Pipeline error on text input")
        await status_msg.edit_text(f"Something went wrong: {e}")


# ── error handler ─────────────────────────────────────────────────────────────

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Unhandled exception", exc_info=context.error)
    if isinstance(update, Update) and update.message:
        await update.message.reply_text("An unexpected error occurred. Please try again.")


# ── entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set in your .env file")

    app = Application.builder().token(token).build()

    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(URL_PATTERN) & filters.TEXT, handle_url)],
        states={
            WAITING_FOR_MANUAL_CONTENT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_manual_content)
            ],
        },
        fallbacks=[CommandHandler("start", start)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(conv_handler)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_error_handler(error_handler)

    logger.info("Telegram bot polling...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
