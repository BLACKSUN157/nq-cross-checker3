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

        print(f"\n🕒 [{name}] 偵測時間：{now}（資料時間：{last_time}）")

        if abs(last_ma5 - last_ma40) < 3:
            msg = (
                f"⚠️ [{name}] MA5 與 MA40 接近（< 3 點）\n"
                f"時間：{now}\n"
                f"價格：{last_price}\n"
                f"MA5: {last_ma5:.2f}\n"
                f"MA40: {last_ma40:.2f}"
            )
            print(msg)
            send_telegram(msg)
            return msg
        else:
            status = f"📉 [{name}] 無接近訊號\n價格：{last_price}（MA5: {last_ma5:.2f}, MA40: {last_ma40:.2f}）"
            print(status)
            send_telegram(status)
            return status

    except Exception as e:
        err_msg = f"⚠️ [{name}] 發生錯誤：{e}"
        print(err_msg)
        return err_msg

# === 路由：每次 Ping 都偵測兩個商品 ===
@app.route('/')
def home():
    result_nq = detect_cross('NQ=F', name="小那斯達克")
    result_txf = detect_cross('TXF1!', name="台指期")
    return f"{result_nq}\n\n{result_txf}"

# === Flask 主程式入口 ===
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)

