from flask import Flask
from apscheduler.schedulers.background import BackgroundScheduler
import yfinance as yf
import pandas as pd
import requests
from datetime import datetime, timedelta

# === Telegram 設定 ===
TELEGRAM_TOKEN = '8116446503:AAEuE74_HF0pITQ0k7H5Dy3Dp9-WuMHWY94'
TELEGRAM_CHAT_ID = '8163295591'

# === Flask 初始化 ===
app = Flask(__name__)

# === 全域變數 ===
# 每個標的獨立追蹤狀態
market_states = {
    "NQ=F": {"last_signal": None, "in_position": None},
    "GC=F": {"last_signal": None, "in_position": None},
    "ES=F": {"last_signal": None, "in_position": None},
    "YM=F": {"last_signal": None, "in_position": None},
    "^TWII": {"last_signal": None, "in_position": None},
}

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

# === 主策略（多標的） ===
def macd_strategy(symbol="NQ=F"):
    try:
        state = market_states[symbol]

        # 只抓 5 分鐘資料
        df = yf.download(symbol, interval="30m", period="12d", auto_adjust=False)

        if df.empty:
            print(f"{symbol} 資料不足")
            return

        df = calc_indicators(df)
        latest = df.iloc[[-1]].copy()  # 保證是 DataFrame
        prev = df.iloc[[-2]].copy()

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # === 把 MACD 和 Signal 轉 float，避免 Series 錯誤 ===
        prev_macd = prev["MACD"].iloc[0].item()
        prev_signal = prev["Signal"].iloc[0].item()
        latest_macd = latest["MACD"].iloc[0].item()
        latest_signal = latest["Signal"].iloc[0].item()

        # === 進場訊號 ===
        signal = None
        if prev_macd < prev_signal and latest_macd > latest_signal:
            signal = "多"
            msg = f"✅ {now}\n{symbol} 5分MACD黃金交叉 → 進場做多"
        elif prev_macd > prev_signal and latest_macd < latest_signal:
            signal = "空"
            msg = f"✅ {now}\n{symbol} 5分MACD死亡交叉 → 進場做空"

        # === 平倉條件 (只看均線，不再考慮 EXIT_LEVELS) ===
        close_price = latest["Close"].iloc[0].item()
        ma40 = None if pd.isna(latest["MA40"].iloc[0]) else latest["MA40"].iloc[0].item()
        ma320 = None if pd.isna(latest["MA320"].iloc[0]) else latest["MA320"].iloc[0].item()

        near_ma40 = ma40 is not None and abs(close_price - ma40) / close_price < 0.0007  # 0.07%
        near_ma320 = ma320 is not None and abs(close_price - ma320) / close_price < 0.0007

        if state["in_position"] and (near_ma40 or near_ma320):
            msg = f"🔔 {now}\n{symbol} 指數 {close_price:.2f} 接近 MA40/MA320 → 平倉"
            print(msg)
            send_telegram(msg)
            state["in_position"] = None
            state["last_signal"] = None
            return

        # === 新訊號才發送 ===
        if signal and signal != state["last_signal"]:
            print(msg)
            send_telegram(msg)
            state["last_signal"] = signal
            state["in_position"] = signal
        else:
            print(f"{now} {symbol} 狀態: {state['in_position'] or '觀望'} (無新訊號)")

    except Exception as e:
        print(f"{symbol} 程式錯誤:", e)
        send_telegram(f"❗{symbol} 策略執行錯誤: {e}")

# === Scheduler (每 30 秒執行一次，每個標的錯開 5 秒) ===
scheduler = BackgroundScheduler()
for i, symbol in enumerate(market_states.keys()):
    scheduler.add_job(
        macd_strategy,
        "interval",
        seconds=30,
        args=[symbol],
        next_run_time=datetime.now() + timedelta(seconds=i * 5)  # ✅ 錯開 5 秒
    )
scheduler.start()

@app.route("/")
def home():
    return "📈 多市場 MACD 策略運行中 (NQ=F, GC=F, ES=F, YM=F, ^TWII，每 30 秒檢查一次，任務錯開 5 秒)..."

if __name__ == "__main__":
    print("📉 多市場 MACD 監控啟動 (Ctrl+C 可停止)")
    app.run(host="0.0.0.0", port=8080)
