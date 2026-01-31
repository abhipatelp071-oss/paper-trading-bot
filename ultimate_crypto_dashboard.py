import requests, pandas as pd, time, os
from datetime import datetime

# ================= CONFIG =================
TIMEFRAMES = ["5m", "15m"]
LIMIT = 100
CAPITAL = 10.0
LEVERAGE = 5
TRADE_MARGIN = 5.0   # margin per trade
MAX_OPEN_TRADES = 2

used_margin = 0.0
day_pnl = 0.0
open_trades = []
trade_history = []

# ================= 100 COINS =================
COINS = [
"BTCUSDT","ETHUSDT","BNBUSDT","SOLUSDT","XRPUSDT","ADAUSDT","AVAXUSDT","DOTUSDT",
"LINKUSDT","MATICUSDT","LTCUSDT","TRXUSDT","ATOMUSDT","OPUSDT","ARBUSDT","NEARUSDT",
"APTUSDT","FILUSDT","INJUSDT","RNDRUSDT","SUIUSDT","SEIUSDT","PEPEUSDT","DOGEUSDT",
"SHIBUSDT","WIFUSDT","BONKUSDT","FTMUSDT","ICPUSDT","EOSUSDT","ETCUSDT","XLMUSDT",
"UNIUSDT","AAVEUSDT","AXSUSDT","SANDUSDT","MANAUSDT","GALAUSDT","CHZUSDT","CRVUSDT",
"DYDXUSDT","ORDIUSDT","TIAUSDT","JUPUSDT","PYTHUSDT","STRKUSDT","ENAUSDT","BLURUSDT",
"GMXUSDT","MINAUSDT","ZILUSDT","KAVAUSDT","RUNEUSDT","ROSEUSDT","ALGOUSDT","NEOUSDT",
"XTZUSDT","MASKUSDT","ANKRUSDT","HOTUSDT","IOTAUSDT","WAVESUSDT","KSMUSDT","STXUSDT",
"IMXUSDT","ENSUSDT","ILVUSDT","CTSIUSDT","MTLUSDT","SXPUSDT","RSRUSDT","COTIUSDT",
"SKLUSDT","CELOUSDT","UMAUSDT","1INCHUSDT","YFIUSDT","OCEANUSDT","API3USDT","IDUSDT",
"ACHUSDT","BICOUSDT","LRCUSDT","BALUSDT","QTUMUSDT","NEOUSDT","ZENUSDT","DASHUSDT"
]

# ================= DATA =================
def fetch(symbol, tf):
    url = "https://api.binance.com/api/v3/klines"
    data = requests.get(url, params={
        "symbol": symbol,
        "interval": tf,
        "limit": LIMIT
    }).json()

    df = pd.DataFrame(data, columns=["t","o","h","l","c","v","_","_","_","_","_","_"])
    df[["o","h","l","c","v"]] = df[["o","h","l","c","v"]].astype(float)
    return df

# ================= INDICATORS =================
def indicators(df):
    df["ema20"] = df["c"].ewm(span=20).mean()
    df["ema50"] = df["c"].ewm(span=50).mean()

    delta = df["c"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    rs = gain.rolling(14).mean() / loss.rolling(14).mean()
    df["rsi"] = 100 - (100 / (1 + rs))

    tp = (df["h"] + df["l"] + df["c"]) / 3
    df["vwap"] = (tp * df["v"]).cumsum() / df["v"].cumsum()
    return df

# ================= SIGNAL =================
def get_signal(symbol):
    directions = []

    for tf in TIMEFRAMES:
        df = indicators(fetch(symbol, tf))
        last = df.iloc[-1]

        if last.c > last.vwap and last.ema20 > last.ema50 and last.rsi > 50:
            directions.append("BUY")
        elif last.c < last.vwap and last.ema20 < last.ema50 and last.rsi < 50:
            directions.append("SELL")

    if directions.count("BUY") == 2:
        return "BUY", last
    if directions.count("SELL") == 2:
        return "SELL", last
    return None, last

# ================= TRADE OPEN =================
def open_trade(symbol, side, price):
    global used_margin

    if symbol in [t["coin"] for t in open_trades]:
        return

    if used_margin + TRADE_MARGIN > CAPITAL:
        return

    qty = (TRADE_MARGIN * LEVERAGE) / price

    sl = price * (0.99 if side == "BUY" else 1.01)
    tp = price * (1.02 if side == "BUY" else 0.98)

    used_margin += TRADE_MARGIN

    open_trades.append({
        "coin": symbol,
        "side": side,
        "entry": price,
        "sl": sl,
        "tp": tp,
        "qty": qty,
        "margin": TRADE_MARGIN
    })

# ================= PNL CALC =================
def floating_pnl(price, trade):
    diff = (price - trade["entry"]) if trade["side"] == "BUY" else (trade["entry"] - price)
    return diff * trade["qty"]

# ================= DASHBOARD =================
def clear():
    os.system("cls" if os.name == "nt" else "clear")

def header():
    print("="*70)
    print("📊 INSTITUTIONAL CRYPTO TRADING TERMINAL")
    print("⏰", datetime.now().strftime("%d-%m-%Y %H:%M:%S"))
    print("="*70)
    print(f"💰 CAPITAL     : {round(CAPITAL,2)} USDT")
    print(f"📉 USED MARGIN : {round(used_margin,2)} USDT")
    print(f"📈 DAY PnL     : {round(day_pnl,2)} USDT")
    print("="*70)

def scanner():
    print("\n────────── COIN SCANNER (5m + 15m) ──────────")
    shown = 0

    for coin in COINS:
        try:
            side, last = get_signal(coin)
            if side and shown < 10:
                print(f"{coin:<10} | {side:<4} | Price {round(last.c,4)} | RSI {round(last.rsi,1)}")
                shown += 1
                if len(open_trades) < MAX_OPEN_TRADES:
                    open_trade(coin, side, last.c)
        except:
            pass

def open_trades_view():
    print("\n────────── OPEN TRADES ──────────")
    if not open_trades:
        print("No open trades")
        return

    for t in open_trades:
        price = fetch(t["coin"], "5m").iloc[-1].c
        pnl = floating_pnl(price, t)
        print(
            f"{t['coin']} | {t['side']} | Entry {round(t['entry'],4)} | "
            f"SL {round(t['sl'],4)} | TP {round(t['tp'],4)} | "
            f"PnL {round(pnl,2)}"
        )

def history_view():
    print("\n────────── LAST 5 CLOSED TRADES ──────────")
    if not trade_history:
        print("No trades yet")
    for t in trade_history[-5:]:
        print(t)

# ================= MAIN LOOP =================
while True:
    clear()
    header()
    scanner()
    open_trades_view()
    history_view()
    time.sleep(10)
