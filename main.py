from flask import Flask
from apscheduler.schedulers.background import BackgroundScheduler
import yfinance as yf
import pandas as pd
import requests
from datetime import datetime

# === Telegram 設定 ===
TELEGRAM_TOKEN = '8116446503:AAEuE74_HF0pITQ0k7H5Dy3Dp9-WuMHWY94'
TELEGRAM_CHAT_ID = '8163295591'

# === Flask 初始化 ===
app = Flask(__name__)

# === 全域變數：紀錄上一次的狀態，避免重複發訊息 ===
last_signal = None  

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": msg}
    try:
        requests.post(url, data=payload)
    except Exception as e:
        print("Telegram 發送失敗:", e)

# === 計算 MACD ===
def calc_macd(df, fast=12, slow=26, signal=9):
    df["EMA_fast"] = df["Close"].ewm(span=fast, adjust=False).mean()
    df["EMA_slow"] = df["Close"].ewm(span=slow, adjust=False).mean()
    df["MACD"] = df["EMA_fast"] - df["EMA_slow"]
    df["Signal"] = df["MACD"].ewm(span=signal, adjust=False).mean()
    return df

# === 取得 MACD 狀態 ===
def get_macd_state(df):
    latest = df.iloc[-1]
    if latest["MACD"] > latest["Signal"]:
        return "多頭"
    elif latest["MACD"] < latest["Signal"]:
        return "空頭"
    else:
        return "觀望"

# === 主策略 ===
def macd_strategy():
    global last_signal
    try:
        # 抓取 1 分鐘與 5 分鐘資料
        df_1m = yf.download("NQ=F", interval="1m", period="1d")
        df_5m = yf.download("NQ=F", interval="5m", period="1d")

        if df_1m.empty or df_5m.empty:
            print("資料不足")
            return

        # 計算 MACD
        df_1m = calc_macd(df_1m)
        df_5m = calc_macd(df_5m)

        state_1m = get_macd_state(df_1m)
        state_5m = get_macd_state(df_5m)

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # === 判斷進出場邏輯 ===
        if state_5m == "多頭" and state_1m == "多頭":
            signal = "做多"
            msg = f"✅ {now}\n5分多頭 + 1分多頭 → 進場 {signal}"
        elif state_5m == "空頭" and state_1m == "空頭":
            signal = "做空"
            msg = f"✅ {now}\n5分空頭 + 1分空頭 → 進場 {signal}"
        else:
            signal = "觀望"
            msg = f"❌ {now}\n1分與5分 MACD 不一致 → 出場 / 觀望\n5分:{state_5m} | 1分:{state_1m}"

        # === 僅在訊號變化時發送 ===
        if signal != last_signal:
            print(msg)
            send_telegram(msg)
            last_signal = signal
        else:
            print(f"{now} 狀態維持: {signal} (不重複發送)")

    except Exception as e:
        print("程式錯誤:", e)
        send_telegram(f"❗策略執行錯誤: {e}")

# === Scheduler (每 30 秒執行一次) ===
scheduler = BackgroundScheduler()
scheduler.add_job(macd_strategy, "interval", seconds=30)
scheduler.start()

@app.route("/")
def home():
    return "📈 MACD 多週期共振監控運行中 (每 30 秒檢查一次，狀態改變才推送)..."

if __name__ == "__main__":
    print("📉 MACD 多週期共振監控啟動，每 30 秒檢查一次... (Ctrl+C 可停止)")
    app.run(host="0.0.0.0", port=8080)






