"""TikTok video downloader using yt-dlp."""

import os
import tempfile
import yt_dlp


class TikTokDownloader:
    """Handles downloading TikTok videos to temporary files."""

    def __init__(self):
        self.temp_dir = tempfile.mkdtemp(prefix="tiktok_")

    def download_video(self, url: str) -> str:
        """
        Download a TikTok video and return the path to the file.
        Raises ValueError if the URL is not a valid TikTok video.
        """
        ydl_opts = {
            "outtmpl": os.path.join(self.temp_dir, "%(id)s.%(ext)s"),
            "format": "best",
            "quiet": True,
            "no_warnings": True,
            "extract_flat": False,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)

            if not info:
                raise ValueError("Could not extract video info")

            # Determine file extension
            ext = info.get("ext", "mp4")
            video_id = info.get("id", "video")
            expected_path = os.path.join(self.temp_dir, f"{video_id}.{ext}")

            # yt-dlp may merge formats; check for the actual file
            if os.path.exists(expected_path):
                return expected_path

            # Fallback: find the file in temp dir
            for f in os.listdir(self.temp_dir):
                if f.endswith((".mp4", ".webm", ".mkv")):
                    return os.path.join(self.temp_dir, f)

            raise ValueError("Downloaded file not found")

    def cleanup(self):
        """Remove all temporary files."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)
        self.temp_dir = tempfile.mkdtemp(prefix="tiktok_")

    def __del__(self):
        self.cleanup()
