"""Entry point for SWTikSaver Telegram bot on Render."""

import os
import sys
import logging

from bot import TikTokSaverBot

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("swtiksaver")


def main():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error(
            "TELEGRAM_BOT_TOKEN environment variable is not set. "
            "Set it in Render dashboard under 'Environment Variables'."
        )
        sys.exit(1)

    logger.info("Starting SWTikSaver bot...")
    bot = TikTokSaverBot(token)
    bot.run()


if __name__ == "__main__":
    main()
