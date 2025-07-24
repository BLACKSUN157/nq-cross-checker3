from flask import Flask
from apscheduler.schedulers.background import BackgroundScheduler
import yfinance as yf
import pandas as pd
import requests
from datetime import datetime

# === Telegram 設定 ===
TELEGRAM_TOKEN = '8116446503:AAEuE74_HF0pITQ0k7H5Dy3Dp9-WuMHWY94'
TELEGRAM_CHAT_ID = '8163295591'

# === 指數清單 ===
INDEX_LIST = [
    ("NQ=F", "小那斯達克"),
    ("YM=F", "小道瓊"),
    ("ES=F", "小S&P"),
    ("GC=F", "小黃金"),
    ("^TWII", "富時台灣指")  # 注意：此為現貨指數，不是期貨，Yahoo 上找不到 TXF1! 類期貨資料
]

# === App 初始化 ===
app = Flask(__name__)
scheduler = BackgroundScheduler()
current_index = {"i": 0}  # 使用 mutable dict 以便跨排程記錄 index

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {'chat_id': TELEGRAM_CHAT_ID, 'text': message}
    try:
        requests.post(url, data=payload)
    except Exception as e:
        print(f"❌ 發送 Telegram 失敗: {e}")

def detect_cross(symbol, name=""):
    interval = '5m'
    period = '5d'

    try:
        data = yf.download(tickers=symbol, interval=interval, period=period, auto_adjust=False, progress=False)
        if data.empty:
            print(f"❌ [{name}] 資料為空")
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
        threshold = last_price * 0.000257  # 約等於 0.0257%

        print(f"\n🕒 [{name}] 偵測時間：{now}（資料時間：{last_time}）")
        messages = []

        if abs(last_ma5 - last_ma40) < threshold:
            msg = (
                f"⚠️ [{name}] MA5 與 MA40 接近（小於 0.0257%）\n"
                f"時間：{now}\n"
                f"價格：{last_price}\n"
                f"MA5: {last_ma5:.2f}\n"
                f"MA40: {last_ma40:.2f}"
            )
            messages.append(msg)
            send_telegram(msg)

        if abs(bias) > 0.5:
            bias_msg = (
                f"📊 [{name}] 價格乖離警告\n"
                f"時間：{now}\n"
                f"價格：{last_price}\n"
                f"MA40: {last_ma40:.2f}\n"
                f"乖離率: {bias:.2f}%"
            )
            messages.append(bias_msg)
            send_telegram(bias_msg)

        if not messages:
            print(f"📉 [{name}] 無接近或乖離訊號（乖離率 {bias:.2f}%，門檻 {threshold:.2f}）")

    except Exception as e:
        print(f"⚠️ [{name}] 發生錯誤：{e}")

# === 輪詢任務：每分鐘偵測一個指數 ===
def scheduled_check():
    i = current_index["i"]
    symbol, name = INDEX_LIST[i]
    detect_cross(symbol, name)
    current_index["i"] = (i + 1) % len(INDEX_LIST)

# === 頁面測試用 ===
@app.route('/')
def home():
    return "📡 指數輪流偵測服務已啟動"

# === 主程式 ===
if __name__ == '__main__':
    scheduler.add_job(scheduled_check, 'interval', minutes=1)
    scheduler.start()
    print("✅ 每分鐘輪流偵測指數中...")
    app.run(host='0.0.0.0', port=8080)



