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

# === 全域變數 ===
last_signal = None  
in_position = None   # "多", "空", or None

# === 指定的 5 個平倉價位 ===
EXIT_LEVELS = [23416, 23371, 23613, 23645,23645]  # 你可以改這裡

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": msg}
    try:
        requests.post(url, data=payload)
    except Exception as e:
        print("Telegram 發送失敗:", e)

# === 計算 MACD + 均線 ===
def calc_indicators(df, fast=12, slow=26, signal=9):
    df["EMA_fast"] = df["Close"].ewm(span=fast, adjust=False).mean()
    df["EMA_slow"] = df["Close"].ewm(span=slow, adjust=False).mean()
    df["MACD"] = df["EMA_fast"] - df["EMA_slow"]
    df["Signal"] = df["MACD"].ewm(span=signal, adjust=False).mean()
    df["MA40"] = df["Close"].rolling(window=40).mean()
    df["MA320"] = df["Close"].rolling(window=320).mean()
    return df

# === 主策略 ===
def macd_strategy():
    global last_signal, in_position
    try:
        # 只抓 5 分鐘資料
        df = yf.download("NQ=F", interval="5m", period="2d")

        if df.empty:
            print("資料不足")
            return

        df = calc_indicators(df)
        latest = df.iloc[-1]
        prev = df.iloc[-2]

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # === 進場訊號 ===
        signal = None
        if prev["MACD"] < prev["Signal"] and latest["MACD"] > latest["Signal"]:
            signal = "多"
            msg = f"✅ {now}\n5分MACD黃金交叉 → 進場做多"
        elif prev["MACD"] > prev["Signal"] and latest["MACD"] < latest["Signal"]:
            signal = "空"
            msg = f"✅ {now}\n5分MACD死亡交叉 → 進場做空"

        # === 平倉條件 ===
        close_price = float(latest["Close"])
        ma40 = float(latest["MA40"]) if not pd.isna(latest["MA40"]) else None
        ma320 = float(latest["MA320"]) if not pd.isna(latest["MA320"]) else None

        near_ma40 = ma40 is not None and abs(close_price - ma40) / close_price < 0.0007  # 0.07%
        near_ma320 = ma320 is not None and abs(close_price - ma320) / close_price < 0.0007
        hit_exit_level = any(abs(close_price - lvl) < 13 for lvl in EXIT_LEVELS)  # 誤差 5 點內算命中

        if in_position and (near_ma40 or near_ma320 or hit_exit_level):
            msg = f"🔔 {now}\n指數 {close_price:.2f} 接近 MA40/MA320 或指定價位 → 平倉"
            print(msg)
            send_telegram(msg)
            in_position = None
            last_signal = None
            return

        # === 新訊號才發送 ===
        if signal and signal != last_signal:
            print(msg)
            send_telegram(msg)
            last_signal = signal
            in_position = signal
        else:
            print(f"{now} 狀態: {in_position or '觀望'} (無新訊號)")

    except Exception as e:
        print("程式錯誤:", e)
        send_telegram(f"❗策略執行錯誤: {e}")

# === Scheduler (每 30 秒執行一次) ===
scheduler = BackgroundScheduler()
scheduler.add_job(macd_strategy, "interval", seconds=30)
scheduler.start()

@app.route("/")
def home():
    return "📈 5分MACD 黃金交叉/死亡交叉策略運行中 (每 30 秒檢查一次)..."

if __name__ == "__main__":
    print("📉 5分MACD 黃金交叉/死亡交叉監控啟動 (Ctrl+C 可停止)")
    app.run(host="0.0.0.0", port=8080)








