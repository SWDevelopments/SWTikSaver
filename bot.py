"""Telegram bot handlers for SWTikSaver."""

import logging
from telegram import Update, Video
from telegram.ext import Application, MessageHandler, filters, ContextTypes

from tiktok_downloader import TikTokDownloader

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


class TikTokSaverBot:
    """Telegram bot that saves TikTok videos on URL share."""

    def __init__(self, token: str):
        self.token = token
        self.downloader = TikTokDownloader()
        self.app = None

    def build_application(self) -> Application:
        """Build and configure the bot application."""
        self.app = Application.builder().token(self.token).build()

        # Handle any text message that looks like a TikTok URL
        handler = MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            self.handle_message,
        )
        self.app.add_handler(handler)

        return self.app

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Process incoming messages and download TikTok videos."""
        message = update.message
        if not message or not message.text:
            return

        text = message.text.strip()

        # Check if it's a TikTok URL
        if not self._is_tiktok_url(text):
            return

        user = message.from_user
        logger.info("TikTok URL from %s (%s): %s", user.first_name, user.id, text)

        # Send loading message
        loading_msg = await message.reply_text(
            "🎵 Downloading TikTok video...\nPlease wait a moment!"
        )

        try:
            video_path = self.downloader.download_video(text)
            await loading_msg.edit_text("✅ Video downloaded! Sending now...")

            with open(video_path, "rb") as video_file:
                await message.reply_video(
                    video=video_file,
                    caption="📥 Downloaded with SWTikSaver",
                )

            await loading_msg.delete()

        except Exception as e:
            logger.error("Error downloading video: %s", e)
            await loading_msg.edit_text(
                "⚠️ Sorry, I couldn't download this video.\n"
                "The link might be invalid, private, or TikTok may have changed their format.\n"
                "Please try again later or send another link."
            )

    def _is_tiktok_url(self, text: str) -> bool:
        """Check if text contains a TikTok video URL."""
        tiktok_domains = [
            "tiktok.com",
            "vm.tiktok.com",
            "vt.tiktok.com",
        ]
        return any(domain in text.lower() for domain in tiktok_domains)

    def run(self):
        """Start the bot."""
        self.build_application()
        logger.info("SWTikSaver bot is starting...")
        self.app.run_polling(allowed_updates=Update.ALL_TYPES)
