from flask import Flask
from apscheduler.schedulers.background import BackgroundScheduler
import yfinance as yf
import pandas as pd
import requests
from datetime import datetime
import time

# === Telegram 設定 ===
TELEGRAM_TOKEN = '8116446503:AAEuE74_HF0pITQ0k7H5Dy3Dp9-WuMHWY94'
TELEGRAM_CHAT_ID = '8163295591'

# === Flask App 初始化 ===
app = Flask(__name__)

# === 指數清單與名稱 ===
SYMBOLS = [
    ('NQ=F', '小那斯達克'),
    ('YM=F', '小道瓊'),
    ('ES=F', '小S&P'),
    ('GC=F', '小黃金'),
    ('^FTSE', '富時台灣指數')
]

current_index = 0  # 用於輪替追蹤

# === 發送 Telegram 訊息 ===
def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': message
    }
    try:
        requests.post(url, data=payload)
    except Exception as e:
        print(f"❌ 發送 Telegram 失敗: {e}")

# === 技術指標偵測函式 ===
def detect_cross(symbol, name=""):
    interval = '5m'
    period = '5d'
    try:
        data = yf.download(tickers=symbol, interval=interval, period=period, auto_adjust=False, progress=False)

        if data.empty:
            msg = f"❌ [{name}] 資料為空"
            print(msg)
            send_telegram(msg)
            return

        data['MA5'] = data['Close'].rolling(window=5).mean()
        data['MA40'] = data['Close'].rolling(window=40).mean()
        data.dropna(inplace=True)

        last_price = data['Close'].iloc[-1]
        last_ma5 = data['MA5'].iloc[-1]
        last_ma40 = data['MA40'].iloc[-1]
        last_time = data.index[-1]
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        bias = (last_price - last_ma40) / last_ma40 * 100
        threshold = last_price * 0.000257  # 約 0.0257%

        print(f"\n🕒 [{name}] 偵測時間：{now}（資料時間：{last_time}）")

        messages = []

        if abs(last_ma5 - last_ma40) < threshold:
            msg = (
                f"⚠️ [{name}] MA5 與 MA40 接近（小於 {threshold:.2f} 點）\n"
                f"時間：{now}\n"
                f"價格：{last_price}\n"
                f"MA5: {last_ma5:.2f}\n"
                f"MA40: {last_ma40:.2f}"
            )
            messages.append(msg)

        if abs(bias) > 0.7:
            bias_msg = (
                f"📊 [{name}] 價格乖離警告\n"
                f"時間：{now}\n"
                f"價格：{last_price}\n"
                f"MA40: {last_ma40:.2f}\n"
                f"乖離率: {bias:.2f}%"
            )
            messages.append(bias_msg)

        if not messages:
            status = (
                f"📉 [{name}] 無接近或乖離訊號\n"
                f"時間：{now}\n"
                f"價格：{last_price}（MA5: {last_ma5:.2f}, MA40: {last_ma40:.2f}, 乖離率: {bias:.2f}%）"
            )
            messages.append(status)

        for msg in messages:
            send_telegram(msg)

    except Exception as e:
        err_msg = f"⚠️ [{name}] 發生錯誤：{e}"
        print(err_msg)
        send_telegram(err_msg)

# === 輪流排程指數偵測 ===
def schedule_next():
    global current_index
    symbol, name = SYMBOLS[current_index]
    detect_cross(symbol, name)
    current_index = (current_index + 1) % len(SYMBOLS)

# === 啟動排程器 ===
scheduler = BackgroundScheduler()
scheduler.add_job(schedule_next, 'interval', minutes=1)
scheduler.start()

# === Flask 根路由 ===
@app.route('/')
def home():
    return "✅ 技術指標監控中... 每分鐘輪流偵測一個指數。"

# === Flask 主程式 ===
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)



