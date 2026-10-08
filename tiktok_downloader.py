"""TikTok video downloader using yt-dlp."""

import os
import re
import tempfile
import shutil

import yt_dlp


TIKTOK_URL_PATTERNS = [
    re.compile(r"tiktok\.com/[:@]/[\w\.\-]+/video/(\d+)", re.IGNORECASE),
    re.compile(r"tiktok\.com/[:@]/[\w\.\-]+/status/(\d+)", re.IGNORECASE),
    re.compile(r"tiktok\.com/[:@]/[\w\.\-]+/video/+", re.IGNORECASE),
    re.compile(r"tiktok\.com/[:@]/[\w\.\-]+/status/+", re.IGNORECASE),
    re.compile(r"tiktok\.com/[:@]/[\w\.\-]+/", re.IGNORECASE),
    re.compile(r"vm\.tiktok\.com/[\w\-]+/?", re.IGNORECASE),
    re.compile(r"vt\.tiktok\.com/[\w\-]+/?", re.IGNORECASE),
    re.compile(r"www\.tiktok\.com/t/[\w]+", re.IGNORECASE),
    re.compile(r"m\.tiktok\.com/[\w\-]+/?", re.IGNORECASE),
]

# URL patterns that look like TikTok but are NOT downloadable videos
NON_VIDEO_PATTERNS = [
    re.compile(r"/photo/", re.IGNORECASE),       # TikTok photo mode
    re.compile(r"/live/", re.IGNORECASE),         # Live streams
    re.compile(r"/live_stream/", re.IGNORECASE),
]


def is_tiktok_url(text: str) -> bool:
    """Check if text contains any known TikTok URL pattern."""
    text = text.strip()
    for pattern in TIKTOK_URL_PATTERNS:
        if pattern.match(text):
            return True
    return any(domain in text.lower() for domain in [
        "tiktok.com", "vm.tiktok.com", "vt.tiktok.com", "m.tiktok.com"
    ])


def is_video_url(url: str) -> bool:
    """
    Check if a TikTok URL points to a downloadable video.
    Returns False for photo mode, live streams, etc.
    """
    for pattern in NON_VIDEO_PATTERNS:
        if pattern.search(url):
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
            "format": "best[ext=mp4]/best",
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
            if os.path.exists(expected):
                return expected

            for ext_candidate in ["mp4", "webm", "mkv"]:
                candidate = os.path.join(self.temp_dir, f"{video_id}.{ext_candidate}")
                if os.path.exists(candidate):
                    return candidate

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
