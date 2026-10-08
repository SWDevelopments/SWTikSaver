"""Telegram bot handlers for SWTikSaver."""

import asyncio
import logging
import os
import time
from datetime import datetime, timedelta, timezone

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

from tiktok_downloader import TikTokDownloader, is_tiktok_url

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

SCAN_LOOKBACK_SECONDS = 300  # 5 minutes


class TikTokSaverBot:
    """Telegram bot that saves TikTok videos on URL share."""

    def __init__(self, token: str):
        self.token = token
        self.downloader = TikTokDownloader()
        self.app = None

    def build_application(self) -> Application:
        """Build and configure the bot application."""
        self.app = Application.builder().token(self.token).build()

        self.app.add_handler(CommandHandler("start", self.handle_start))
        self.app.add_handler(CommandHandler("help", self.handle_help))

        handler = MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            self.handle_message,
        )
        self.app.add_handler(handler)

        return self.app

    async def handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send a welcome message when user sends /start."""
        if not update.message:
            return

        user = update.effective_user
        await update.message.reply_text(
            f"👋 Hi {user.first_name}! I'm SWTikSaver.\n\n"
            f"📥 Send me any TikTok video link and I'll download it for you.\n\n"
            f"Supported links:\n"
            f"  • tiktok.com/video/...\n"
            f"  • vm.tiktok.com/...\n"
            f"  • vt.tiktok.com/...\n"
            f"  • Any TikTok share link\n\n"
            f"Try sending a TikTok URL now! 🎵",
            disable_web_page_preview=True,
        )

    async def handle_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send help information."""
        if not update.message:
            return

        await update.message.reply_text(
            "📖 **SWTikSaver Help**\n\n"
            "Send any TikTok video URL and I'll download & send it back to you.\n\n"
            "Supported URL types:\n"
            "• `tiktok.com/video/ID`\n"
            "• `tiktok.com/@user/status/ID`\n"
            "• `vm.tiktok.com/...`\n"
            "• `vt.tiktok.com/...`\n"
            "• `m.tiktok.com/...`\n"
            "• Any TikTok share link\n\n"
            "Just paste the link — no commands needed!",
            parse_mode="Markdown",
            disable_web_page_preview=True,
        )

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Process incoming messages and download TikTok videos."""
        message = update.message
        if not message or not message.text:
            return

        text = message.text.strip()

        if not is_tiktok_url(text):
            return

        user = message.from_user
        logger.info(
            "TikTok URL from %s (%s): %s",
            user.first_name,
            user.id,
            text,
        )

        loading_msg = await message.reply_text(
            "🎵 Downloading TikTok video...\nPlease wait a moment!"
        )

        try:
            video_path = self.downloader.download_video(text)
            await loading_msg.edit_text("✅ Video downloaded! Sending now...")

            file_size = os.path.getsize(video_path)
            with open(video_path, "rb") as video_file:
                await message.reply_video(
                    video=video_file,
                    caption=f"📥 Downloaded with SWTikSaver ({file_size // 1024} KB)",
                )

            await loading_msg.delete()

        except Exception as e:
            error_msg = str(e)
            logger.error("Error downloading video: %s", error_msg)

            if "copyright" in error_msg.lower() or "private" in error_msg.lower():
                await loading_msg.edit_text(
                    "⚠️ This video might be private, removed, or has download restrictions.\n"
                    "Please try another link."
                )
            elif "unexpected response" in error_msg.lower():
                await loading_msg.edit_text(
                    "⚠️ TikTok's servers returned an unexpected response.\n"
                    "This can happen temporarily — try again in a few moments."
                )
            else:
                await loading_msg.edit_text(
                    "⚠️ Sorry, I couldn't download this video.\n"
                    "The link might be invalid, private, or TikTok may have changed.\n"
                    "Please try again later."
                )

    async def scan_recent_messages(self):
        """Scan for recent unprocessed messages from while bot was offline."""
        if not self.app:
            return

        logger.info("Scanning for recent messages from while bot was offline...")

        try:
            now = int(time.time())
            oldest_allowed = datetime.fromtimestamp(
                now - SCAN_LOOKBACK_SECONDS, tz=timezone.utc
            )

            updates = await self.app.bot.get_updates(
                offset=-1,
                timeout=1,
                allowed_updates=["message"],
            )

            processed = 0
            skipped = 0
            for update in updates:
                if not update.message or not update.message.text:
                    continue

                msg_time = update.message.date
                if msg_time and msg_time >= oldest_allowed:
                    text = update.message.text.strip()
                    if is_tiktok_url(text):
                        user_info = (
                            f"{update.message.from_user.first_name} "
                            f"({update.message.from_user.id})"
                            if update.message.from_user
                            else "unknown"
                        )
                        logger.info(
                            "Found offline message from %s: %s",
                            user_info,
                            text,
                        )
                        try:
                            await update.message.reply_text(
                                "📥 Processing your video from earlier...",
                            )
                            video_path = self.downloader.download_video(text)
                            with open(video_path, "rb") as video_file:
                                await update.message.reply_video(
                                    video=video_file,
                                    caption="📥 Downloaded with SWTikSaver",
                                )
                            processed += 1
                        except Exception as e:
                            logger.warning(
                                "Failed to process offline message: %s", e
                            )
                    else:
                        skipped += 1

            logger.info(
                "Scan complete: processed %d videos, skipped %d non-TikTok messages",
                processed,
                skipped,
            )

        except Exception as e:
            logger.warning("Error scanning recent messages: %s", e)

    async def post_init(self, app: Application):
        """Called after the application is initialized.
        Use this to scan for offline messages before polling starts.
        """
        logger.info("Post-init: scanning for offline messages...")
        await self.scan_recent_messages()
        logger.info("Post-init complete, starting polling...")

    def run(self):
        """Start the bot. PTB handles the event loop internally."""
        self.build_application()

        # Register post_init hook — PTB calls this after setup, before polling
        self.app.post_init = self.post_init

        logger.info("SWTikSaver bot is starting...")
        self.app.run_polling(allowed_updates=Update.ALL_TYPES)
