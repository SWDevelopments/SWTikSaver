# SWTikSaver

A Telegram bot that saves TikTok videos. Send any TikTok URL and get the video back!

**As of October 2026** — uses `python-telegram-bot==22.8` and `yt-dlp==2026.8.19`

## Features

- 📥 Download any TikTok video by sending the link
- 🔗 Supports ALL TikTok URL types:
  - `tiktok.com/@user/video/ID`
  - `tiktok.com/@user/status/ID`
  - `tiktok.com/t/...` (short links)
  - `vm.tiktok.com/...` (share links)
  - `vt.tiktok.com/...` (Tap to view)
  - `m.tiktok.com/...` (mobile)
  - Any link containing a TikTok domain
- 👋 `/start` — welcome message
- 📖 `/help` — usage info
- 🔄 Scans for messages received while bot was offline
- ⏱️ Retries download up to 3 times on failure

## Quick Setup

### 1. Create a Telegram Bot

1. Open Telegram → search **@BotFather**
2. Send `/newbot` → follow prompts → copy the token

### 2. Deploy on Render

**Recommended:** Use a **Background Worker** (not a Web Service).

1. Push this repo to GitHub
2. Go to [render.com](https://render.com) → **New** → **Background Worker**
3. Connect your GitHub repo
4. Configure:
   - **Name:** `swtiksaver`
   - **Region:** closest to you
   - **Branch:** `main`
   - **Runtime:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python worker.py`
   - **Instance Type:** `Free`
5. Add Environment Variable:
   - **Key:** `TELEGRAM_BOT_TOKEN`
   - **Value:** your bot token from BotFather
6. Click **Create Worker**

### 3. Verify Deployment

Check Render logs — you should see:
```
INFO:swtiksaver:Starting SWTikSaver bot...
INFO:bot:SWTikSaver bot is starting...
INFO:telegram.ext.Application - Application started
```

## Usage

1. Open your bot in Telegram
2. Send `/start` for a welcome message
3. Send `/help` for usage info
4. Paste any TikTok video link
5. Bot downloads and sends the video back

If the bot was offline when you sent a link, it will process it when it comes back online (scans last 5 minutes of messages).

## Project Structure

```
.
├── worker.py              # Entry point for Render
├── bot.py                 # Telegram bot (handlers, scanning, URL detection)
├── tiktok_downloader.py   # yt-dlp wrapper with retry logic
├── requirements.txt       # python-telegram-bot==22.8, yt-dlp==2026.8.19
├── Procfile               # Process type for Render
└── README.md
```

## Dependencies

| Package              | Version   | Purpose                        |
|----------------------|-----------|--------------------------------|
| python-telegram-bot  | 22.8      | Telegram Bot API (async)       |
| yt-dlp               | 2026.8.19 | Video downloading              |

## Updating yt-dlp

TikTok changes frequently. If downloads stop working:

```bash
pip install -U yt-dlp
# Update requirements.txt and redeploy
```

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Worker won't start | Check `TELEGRAM_BOT_TOKEN` in Render env vars |
| "No module named 'telegram'" | Ensure build command is `pip install -r requirements.txt` |
| Downloads fail with "unexpected response" | TikTok server issue — retry later, or update yt-dlp |
| Bot not responding | Check Render logs; verify bot not blocked in Telegram |

## License

MIT
