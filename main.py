from flask import Flask
import yfinance as yf
import pandas as pd
import requests
from datetime import datetime

# === Telegram 設定 ===
TELEGRAM_TOKEN = '8116446503:AAEuE74_HF0pITQ0k7H5Dy3Dp9-WuMHWY94'
TELEGRAM_CHAT_ID = '8163295591'

# === Flask App 初始化 ===
app = Flask(__name__)

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

def detect_cross(symbol, name=""):
    interval = '5m'
    period = '5d'

    try:
        data = yf.download(tickers=symbol, interval=interval, period=period, auto_adjust=False, progress=False)

        if data.empty:
            print(f"❌ [{name}] 資料為空")
            return f"[{name}] 資料為空"

        data['MA5'] = data['Close'].rolling(window=5).mean()
        data['MA40'] = data['Close'].rolling(window=40).mean()
        data.dropna(inplace=True)

        last_price = data['Close'].iloc[-1]
        last_ma5 = data['MA5'].iloc[-1]
        last_ma40 = data['MA40'].iloc[-1]
        last_time = data.index[-1]
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        bias = (last_price - last_ma40) / last_ma40 * 100

        print(f"\n🕒 [{name}] 偵測時間：{now}（資料時間：{last_time}）")

        messages = []

        if abs(last_ma5 - last_ma40) < 6:
            msg = (
                f"⚠️ [{name}] MA5 與 MA40 接近（< 6 點）\n"
                f"時間：{now}\n"
                f"價格：{last_price}\n"
                f"MA5: {last_ma5:.2f}\n"
                f"MA40: {last_ma40:.2f}"
            )
            messages.append(msg)
            send_telegram(msg)

        if abs(bias) > 0.49:
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
            status = (
                f"📉 [{name}] 無接近或乖離訊號\n"
                f"價格：{last_price}（MA5: {last_ma5:.2f}, MA40: {last_ma40:.2f}, 乖離率: {bias:.2f}%）"
            )
            messages.append(status)
            send_telegram(status)
            print(status)
            return status
        else:
            return "\n\n".join(messages)

    except Exception as e:
        err_msg = f"⚠️ [{name}] 發生錯誤：{e}"
        print(err_msg)
        return err_msg

# === 路由：只偵測小那斯達克 ===
@app.route('/')
def home():
    result_nq = detect_cross('NQ=F', name="小那斯達克")
    return result_nq

# === Flask 主程式入口 ===
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)




