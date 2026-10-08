# SWTikSaver

A Telegram bot that saves TikTok videos. Send a TikTok URL and get the video back!

**Live as of October 2026** — uses `python-telegram-bot==22.8` and `yt-dlp==2026.8.19`

## Features

- Send any TikTok video link and receive the video file
- Works with `tiktok.com`, `vm.tiktok.com`, and `vt.tiktok.com` links
- Always-on on Render (Background Worker)

## Quick Setup

### 1. Create a Telegram Bot

1. Open Telegram and search for **@BotFather**
2. Send `/newbot` and follow the instructions
3. Copy the **Bot Token** (looks like `123456:ABC-DEF1234...`)

### 2. Deploy on Render

**Recommended:** Use a **Background Worker** (not a Web Service) so the bot stays connected to Telegram's polling API.

1. Push this repo to GitHub
2. Go to [render.com](https://render.com) → **New** → **Background Worker**
3. Connect your GitHub repo
4. Configure:
   - **Name:** `swtiksaver` (or your choice)
   - **Region:** closest to you
   - **Branch:** `main`
   - **Root Directory:** leave blank
   - **Runtime:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python worker.py`
   - **Instance Type:** `Free`
5. Add Environment Variable:
   - **Key:** `TELEGRAM_BOT_TOKEN`
   - **Value:** your bot token from BotFather
6. Click **Create Worker**

> **Web Service alternative:** If you prefer a Web Service, use `python worker.py` as the start command. The free tier spins down after 15 min of inactivity — first message will take ~30s to respond.

### 3. Verify Deployment

Check the Render dashboard logs — you should see:
```
INFO:swtiksaver:Starting SWTikSaver bot...
```

If the worker crashes, check logs for errors.

## Usage

1. Open your bot in Telegram
2. Send `/start` to activate
3. Forward or paste any TikTok video link
4. The bot will download and send the video back

## Project Structure

```
.
├── worker.py              # Entry point for Render (reads env, starts bot)
├── bot.py                 # Telegram bot handler (listens for URLs, replies with video)
├── tiktok_downloader.py   # yt-dlp wrapper for downloading TikTok videos
├── requirements.txt       # python-telegram-bot==22.8, yt-dlp==2026.8.19
├── Procfile               # Process type for Render
└── README.md
```

## Dependencies

| Package              | Version  | Purpose                        |
|----------------------|----------|--------------------------------|
| python-telegram-bot  | 22.8     | Telegram Bot API (async, PTB v22) |
| yt-dlp               | 2026.8.19| Video downloading              |

## Updating yt-dlp

TikTok changes their platform frequently. If downloads stop working, update `yt-dlp`:

```bash
pip install -U yt-dlp
# then update requirements.txt and redeploy
```

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Worker won't start | Check `TELEGRAM_BOT_TOKEN` is set in Render env vars |
| "No module named 'telegram'" | Ensure build command is `pip install -r requirements.txt` |
| Downloads fail | Update `yt-dlp` to latest version |
| Bot not responding | Check Render logs for errors; verify bot is not blocked in Telegram |

## License

MIT
