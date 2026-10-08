"""TikTok video downloader using yt-dlp."""

import os
import re
import tempfile
import shutil

import yt_dlp


# ---------------------------------------------------------------------------
# URL detection
# ---------------------------------------------------------------------------
#
# TikTok serves the same video through many URL shapes. New shapes appear
# regularly (e.g. /t/ short links, vm/vt "share" links, m. mobile, bare
# domain paths without a scheme). We therefore match aggressively against
# anything that looks like a TikTok *post* URL and then let yt-dlp decide
# whether it is actually a downloadable video.
#
# Order matters: the most specific / unambiguous patterns first, then the
# broader fallback patterns.

TIKTOK_URL_PATTERNS = [
    # Standard video links with an explicit numeric ID.
    re.compile(
        r"^(?:https?://)?(?:[a-zA-Z0-9-]+\.)*tiktok\.com/"
        r"[\w.\-]+/video/(?P<id>\d+)",
        re.IGNORECASE,
    ),
    # Standard status links (share links that resolve to a video).
    re.compile(
        r"^(?:https?://)?(?:[a-zA-Z0-9-]+\.)*tiktok\.com/"
        r"[\w.\-]+/status/(?P<id>\d+)",
        re.IGNORECASE,
    ),
    # Short /t/ links (share links that expand to a video).
    re.compile(
        r"^(?:https?://)?"
        r"(?:www\.)?tiktok\.com/t/"
        r"(?P<id>[A-Za-z0-9_\-]+)",
        re.IGNORECASE,
    ),
    # vm.tiktok.com / vt.tiktok.com share links (video/multimedia share).
    re.compile(
        r"^(?:https?://)?"
        r"vm\.tiktok\.com/(?P<id>[A-Za-z0-9_\-]+)/?$",
        re.IGNORECASE,
    ),
    re.compile(
        r"^(?:https?://)?"
        r"vt\.tiktok\.com/(?P<id>[A-Za-z0-9_\-]+)/?$",
        re.IGNORECASE,
    ),
    # m.tiktok.com mobile short links (often /@user/ID or /@user/<uuid>).
    re.compile(
        r"^(?:https?://)?"
        r"m\.tiktok\.com/"
        r"[\w.\-]+/"
        r"(?P<id>[A-Za-z0-9_\-]+)"
        r"(?:/[^\s?#]*)?$",
        re.IGNORECASE,
    ),
    # Generic profile/path links that still resolve to a post page, e.g.
    #   tiktok.com/@user/1234567890123456789
    #   tiktok.com/@user/  (some posts use a trailing path with no explicit
    #                       video/status segment)
    re.compile(
        r"^(?:https?://)?"
        r"(?:www\.)?tiktok\.com/"
        r"[\w.\-]+/"
        r"(?:[a-zA-Z_\-]+/)?"
        r"(?P<id>[A-Za-z0-9_\-]+)"
        r"(?:/[^\s?#]*)?$",
        re.IGNORECASE,
    ),
    # Bare tiktok.com/@user/ or tiktok.com/@user with no trailing ID still
    # opens a profile; these are *not* videos, so we deliberately do NOT
    # match a bare profile-only path here. Instead the domain-level fallback
    # below handles any other tiktok.com string so embedded links are not
    # missed.
    #
    # Anything that contains a tiktok domain is treated as a TikTok link by
    # the domain fallback in is_tiktok_url() below.

    # Broad fallback: catches anything containing one of the known TikTok
    # hostnames (including embedded links inside longer text, bare paths
    # without a scheme, etc.). This is intentionally last so the more precise
    # post-URL patterns above take precedence.
    re.compile(
        r"(?:tiktok\.com|vm\.tiktok\.com|vt\.tiktok\.com|m\.tiktok\.com)",
        re.IGNORECASE,
    ),
]

# URL substrings/paths that indicate TikTok content that is NOT a downloadable
# video. These are checked against the full URL string after a TikTok link is
# detected, so they can reject photo-mode posts, live streams, etc. even when
# the host/path pattern would otherwise match.

NON_VIDEO_SUBSTRINGS = [
    "/photo/",
    "/photos/",
    "/photo_medium/",
    "/live/",
    "/live_stream/",
    "/live_status/",
    "/rituals/",
    "/creator/",
]


def is_tiktok_url(text: str) -> bool:
    """Check if `text` contains / is a TikTok URL.

    Matches:
      - Exact TikTok post URLs (video/status/t/ short links, vm/vt/m)
      - Bare tiktok.com/@user/ID paths, with or without a scheme
      - tiktok.com URLs embedded inside longer text (the domain fallback)
    """
    text = text.strip()
    if not text:
        return False

    # Fast exhaustive match against the specific post patterns first.
    for pattern in TIKTOK_URL_PATTERNS:
        if pattern.search(text):
            return True

    return False


def is_video_url(url: str) -> bool:
    """Return False for TikTok content that is not a downloadable video.

    Checked *after* a TikTok link has been detected. Reject photo mode,
    lives, and similar non-video post types. Everything else is handed to
    yt-dlp, which will reject non-video content itself if needed.
    """
    low = url.lower()
    for needle in NON_VIDEO_SUBSTRINGS:
        if needle in low:
            return False
    return True


class TikTokDownloader:
    """Handles downloading TikTok videos to temporary files."""

    def __init__(self):
        self.temp_dir = tempfile.mkdtemp(prefix="tiktok_")

    def _ensure_dir(self):
        if not os.path.exists(self.temp_dir):
            os.makedirs(self.temp_dir, exist_ok=True)

    def download_video(self, url: str) -> str:
        """Download a TikTok video and return the path to the file."""
        if not is_video_url(url):
            raise ValueError(
                "This TikTok link is not a video (photo mode, live, etc.). "
                "Only video links can be downloaded."
            )

        self._ensure_dir()

        for attempt in range(3):
            try:
                return self._try_download(url, attempt)
            except Exception as e:
                if attempt == 2:
                    raise
                self._cleanup_attempt()
                continue

    def _try_download(self, url: str, attempt: int) -> str:
        ydl_opts = {
            "outtmpl": os.path.join(self.temp_dir, "%(id)s.%(ext)s"),
            "format": "bestvideo+bestaudio/best[ext=mp4]/best",
            "merge_output_format": "mp4",
            "quiet": True,
            "no_warnings": True,
            "extract_flat": False,
            "socket_timeout": 30,
            "retries": 2,
            "fragment_retries": 2,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)

            if not info:
                raise ValueError("Could not extract video info")

            video_id = info.get("id", "")
            ext = info.get("ext", "mp4")

            expected = os.path.join(self.temp_dir, f"{video_id}.{ext}")
            if os.path.exists(expected) and os.path.isfile(expected):
                return expected

            for ext_candidate in ["mp4", "webm", "mkv"]:
                candidate = os.path.join(
                    self.temp_dir, f"{video_id}.{ext_candidate}"
                )
                if os.path.exists(candidate) and os.path.isfile(candidate):
                    return candidate

            # Fallback: pick any file yt-dlp wrote into the temp dir.
            # Some TikTok responses do not expose a clean id/ext pair, so we
            # accept the first file that looks like a real video.
            for f in sorted(os.listdir(self.temp_dir)):
                if f.endswith((".mp4", ".webm", ".mkv")):
                    path = os.path.join(self.temp_dir, f)
                    if os.path.isfile(path) and os.path.getsize(path) > 1000:
                        return path

            raise ValueError("Downloaded file not found after extraction")

    def _cleanup_attempt(self):
        if os.path.exists(self.temp_dir):
            for f in os.listdir(self.temp_dir):
                try:
                    os.remove(os.path.join(self.temp_dir, f))
                except OSError:
                    pass

    def cleanup(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)
        self.temp_dir = tempfile.mkdtemp(prefix="tiktok_")

    def __del__(self):
        try:
            self.cleanup()
        except Exception:
            pass
