from flask import Flask
import yfinance as yf
import pandas as pd
import requests
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler

# === Telegram 設定 ===
TELEGRAM_TOKEN = '8116446503:AAEuE74_HF0pITQ0k7H5Dy3Dp9-WuMHWY94'
TELEGRAM_CHAT_ID = '8163295591'

app = Flask(__name__)

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    requests.post(url, json=payload)

def check_ma_cross():
    symbol = "NQ=F"
    now = datetime.now()
    print(f"🔁 [{now.strftime('%Y-%m-%d %H:%M:%S')}] 檢查中...")
    data = yf.download(tickers=symbol, period="2d", interval="5m")
    if data.empty:
        print("❌ 資料下載失敗")
        return

    data["MA5"] = data["Close"].rolling(window=5).mean()
    data["MA40"] = data["Close"].rolling(window=40).mean()

    if len(data) < 41:
        print("⏳ 資料不足，等待更多資料點")
        return

    latest = data.iloc[-1]
    prev = data.iloc[-2]

    crossed = None
    if prev["MA5"] < prev["MA40"] and latest["MA5"] > latest["MA40"]:
        crossed = "🟢 黃金交叉出現！"
    elif prev["MA5"] > prev["MA40"] and latest["MA5"] < latest["MA40"]:
        crossed = "🔴 死亡交叉出現！"

    if crossed:
        message = f"{crossed}\n時間：{now.strftime('%Y-%m-%d %H:%M')}價格：{latest['Close']:.2f}"
        send_telegram(message)
        print(message)
    else:
        print("❌ 沒有交叉訊號")

scheduler = BackgroundScheduler()
scheduler.add_job(check_ma_cross, 'interval', minutes=5)
scheduler.start()

@app.route('/')
def index():
    return "✅ NQ=F 交叉監控器運行中"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
