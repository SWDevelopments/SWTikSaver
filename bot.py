"""Telegram bot handlers for SWTikSaver."""

import asyncio
import logging
import os
import re
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

from tiktok_downloader import TikTokDownloader, is_tiktok_url, is_video_url

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

SCAN_LOOKBACK_SECONDS = 300


def _first_tiktok_token(text: str) -> str | None:
    """Return the first TikTok URL found in `text`, or None.

    Telegram messages frequently contain a sentence that *contains* a TikTok URL
    rather than being exactly the URL, so we scan for embedded URLs. We also treat
    bare domain/path strings (without a scheme) as valid TikTok links, since users
    paste them often.
    """
    # Fast path: the whole message is already a TikTok URL.
    if is_tiktok_url(text):
        return text

    # Tokenize on whitespace + common wrapping punctuation.
    tokens = re.split(
        r"[\s,;:()|<>\\'\"\\\u201c\u201d\u2018\u2019]+",
        text,
    )
    for token in tokens:
        token = token.strip()
        if not token:
            continue
        if is_tiktok_url(token):
            return token

    return None


class TikTokSaverBot:
    def __init__(self, token: str):
        self.token = token
        self.downloader = TikTokDownloader()
        self.app = None

    def build_application(self) -> Application:
        self.app = Application.builder().token(self.token).build()

        self.app.add_handler(CommandHandler("start", self.handle_start))
        self.app.add_handler(CommandHandler("help", self.handle_help))

        handler = MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            self.handle_message,
        )
        self.app.add_handler(handler)

        return self.app

    def _extract_url_from_message(self, message) -> str | None:
        """Extract a TikTok URL from a message.

        Checks the message text, caption, and replied-to message text/caption.
        Telegram merges forwarded message text into message.text, so forwarded
        links are already covered there; we also inspect the caption because some
        forwarded media posts only carry the text in the caption.

        Returns the first TikTok URL found. If it is a non-video link (photo mode,
        live, etc.) the raw URL is still returned so the caller can reject it with
        a clear message.
        """
        if not message:
            return None

        candidates: list[str] = []

        def _add(text: str | None) -> None:
            if text:
                cleaned = text.strip()
                if cleaned and cleaned not in candidates:
                    candidates.append(cleaned)

        # 1. Message text (covers most forwards whose text is merged in).
        _add(message.text)

        # 2. Caption — forwarded media posts often put the link here.
        _add(message.caption)

        # 3. Reply-to message text/caption.
        reply = message.reply_to_message
        if reply:
            _add(reply.text)
            _add(reply.caption)

        for text in candidates:
            url = _first_tiktok_token(text)
            if url:
                return url

        return None

    async def handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.message:
            return

        user = update.effective_user
        await update.message.reply_text(
            f"👋 Hi {user.first_name}! I'm SWTikSaver.\n\n"
            f"📥 Send me any TikTok video link and I'll download it for you.\n\n"
            f"Supported links (any TikTok content URL):\n"
            f"  • tiktok.com/@user/video/ID\n"
            f"  • tiktok.com/@user/status/ID\n"

            f"  • vm.tiktok.com/...\n"
            f"  • vt.tiktok.com/...\n"
            f"  • m.tiktok.com/...\n"
            f"  • Any tiktok.com/@user/... link\n"
            f"  • Any link containing a TikTok domain\n\n"
            f"💡 You can also reply to a message containing a TikTok link "
            f"or forward a message with a link.\n\n"
            f"Try sending a TikTok URL now! 🎵",
            disable_web_page_preview=True,
        )

    async def handle_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.message:
            return

        await update.message.reply_text(
            "📖 **SWTikSaver Help**\n\n"
            "Send any TikTok video URL and I'll download & send it back to you.\n\n"
            "**Supported URL types:**\n"
            "• `tiktok.com/@user/video/ID`\n"
            "• `tiktok.com/@user/status/ID`\n"
            "• `tiktok.com/t/...` (short links)\n"
            "• `vm.tiktok.com/...`\n"
            "• `vt.tiktok.com/...`\n"
            "• `m.tiktok.com/...`\n"
            "• Any `tiktok.com/@user/...` link\n"
            "• Any link containing a TikTok domain\n\n"
            "**How to use:**\n"
            "• Paste a TikTok link directly\n"
            "• Reply to a message that contains a TikTok link\n"
            "• Forward a message with a TikTok link\n\n"
            "**Not supported:**\n"
            "• TikTok photo mode posts\n"
            "• Live streams\n"
            "• Private/removed videos",
            parse_mode="Markdown",
            disable_web_page_preview=True,
        )

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        message = update.message
        if not message:
            return

        url = self._extract_url_from_message(message)

        if not url:
            return

        user = message.from_user
        chat_title = message.chat.title if message.chat else "DM"
        is_reply = message.reply_to_message is not None
        is_forward = bool(getattr(message, "forward_date", None))

        logger.info(
            "TikTok URL from %s (%s) in %s: %s%s%s",
            user.first_name,
            user.id,
            chat_title,
            url,
            " [reply]" if is_reply else "",
            " [forward]" if is_forward else "",
        )

        # Check if it's a non-video TikTok URL
        if not is_video_url(url):
            loading_msg = await message.reply_text(
                "⚠️ This TikTok link is a photo or live stream, not a video.\n"
                "Only video posts can be downloaded. Please send a video link."
            )
            await asyncio.sleep(5)
            await loading_msg.delete()
            return

        context_note = ""
        if is_reply:
            context_note = "\n(Processing link from replied message)"
        if is_forward:
            context_note = "\n(Processing forwarded link)"

        loading_msg = await message.reply_text(
            f"🎵 Downloading TikTok video...{context_note}\nPlease wait a moment!"
        )

        try:
            video_path = self.downloader.download_video(url)
            await loading_msg.edit_text("✅ Video downloaded! Sending now...")

            file_size = os.path.getsize(video_path)
            with open(video_path, "rb") as video_file:
                caption = f"📥 Downloaded with SWTikSaver ({file_size // 1024} KB)"
                await message.reply_video(
                    video=video_file,
                    caption=caption,
                )

            await loading_msg.delete()

        except ValueError as e:
            logger.warning("Non-retryable error: %s", e)
            await loading_msg.edit_text(f"⚠️ {e}")

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
                    url = self._extract_url_from_message(update.message)
                    if url and is_video_url(url):
                        user_info = (
                            f"{update.message.from_user.first_name} "
                            f"({update.message.from_user.id})"
                            if update.message.from_user
                            else "unknown"
                        )
                        logger.info(
                            "Found offline message from %s: %s",
                            user_info,
                            url,
                        )
                        try:
                            await update.message.reply_text(
                                "📥 Processing your video from earlier...",
                            )
                            video_path = self.downloader.download_video(url)
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
        logger.info("Post-init: scanning for offline messages...")
        await self.scan_recent_messages()
        logger.info("Post-init complete, starting polling...")

    def run(self):
        self.build_application()
        self.app.post_init = self.post_init
        logger.info("SWTikSaver bot is starting...")
        self.app.run_polling(allowed_updates=Update.ALL_TYPES)
