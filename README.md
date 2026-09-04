# Binance Telegram Educational Signal Bot

This project is a **signal-only educational bot**.

It:
- reads public Binance market data;
- checks EMA trend, RSI, MACD and breakout strategies separately;
- sends a Telegram message when at least 3 strategies agree;
- exposes a small HTTP health endpoint for Render Web Service.

It does **not**:
- place Binance orders;
- use Binance trading API keys;
- use leverage;
- auto-trade.

## Render

Language: Python 3

Build Command:
`pip install -r requirements.txt`

Start Command:
`python main.py`

Root Directory: blank

## Environment variables

Set these in Render Environment Variables (do not put secrets in GitHub):

`TELEGRAM_BOT_TOKEN`
`TELEGRAM_CHAT_ID`

The bot token is obtained from Telegram's BotFather. The chat ID is the destination chat/channel where your bot is allowed to post.

For a free/test Render service, select the available $0/month compute option if your account shows one. Free web services may sleep, so continuous 24/7 scanning is not guaranteed.
