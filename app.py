import streamlit as st
import yfinance as yf
import pandas as pd
import ta
import numpy as np

st.set_page_config(page_title="Pro Trading System", layout="wide")

st.title("🚀 Pro Trading System (All Markets)")

# -------------------------
# INPUT
# -------------------------
symbol = st.text_input("Enter Asset", "BTC-USD")

timeframe = st.selectbox(
    "Select Timeframe",
    ["5m", "15m", "1h", "4h", "1d"]
)

indicators = st.multiselect(
    "Select Indicators",
    ["RSI", "MACD", "EMA", "Bollinger Bands", "VWAP"],
    default=["RSI", "MACD", "EMA"]
)

# -------------------------
# MARKET DETECTION
# -------------------------
def detect_market(symbol):
    if "-USD" in symbol:
        return "CRYPTO"
    elif "=X" in symbol:
        return "FOREX"
    elif ".NS" in symbol or ".BO" in symbol:
        return "STOCK"
    else:
        return "UNKNOWN"

# -------------------------
# TIMEFRAME MAP
# -------------------------
def get_interval(tf):
    mapping = {
        "5m": ("5d", "5m"),
        "15m": ("7d", "15m"),
        "1h": ("1mo", "1h"),
        "4h": ("3mo", "1h"),
        "1d": ("6mo", "1d"),
    }
    return mapping[tf]

# -------------------------
# DATA
# -------------------------
def get_data(sym, period, interval):
    data = yf.download(sym, period=period, interval=interval, progress=False)
    if data.empty:
        return None

    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)

    return data.dropna()

# -------------------------
# ANALYSIS
# -------------------------
def analyze(df, indicators):
    data = df.copy()

    for col in ['Close', 'High', 'Low', 'Volume']:
        data[col] = np.array(data[col]).flatten()

    score = 0
    indicator_output = {}

    # RSI
    if "RSI" in indicators:
        rsi = ta.momentum.RSIIndicator(data['Close']).rsi()
        val = rsi.iloc[-1]

        if val < 30:
            sig = "🟢 BUY"
            score += 1
        elif val > 70:
            sig = "🔴 SELL"
            score -= 1
        else:
            sig = "⚪ HOLD"

        indicator_output["RSI"] = {"value": round(val, 2), "signal": sig}

    # MACD
    if "MACD" in indicators:
        macd = ta.trend.MACD(data['Close'])
        macd_val = macd.macd().iloc[-1]
        signal_val = macd.macd_signal().iloc[-1]

        if macd_val > signal_val:
            sig = "🟢 BUY"
            score += 1
        else:
            sig = "🔴 SELL"
            score -= 1

        indicator_output["MACD"] = {
            "macd": round(macd_val, 2),
            "signal_line": round(signal_val, 2),
            "signal": sig
        }

    # EMA
    if "EMA" in indicators:
        ema9 = ta.trend.EMAIndicator(data['Close'], 9).ema_indicator()
        ema21 = ta.trend.EMAIndicator(data['Close'], 21).ema_indicator()

        if ema9.iloc[-1] > ema21.iloc[-1]:
            sig = "🟢 BUY"
            score += 1
        else:
            sig = "🔴 SELL"
            score -= 1

        indicator_output["EMA"] = {
            "EMA 9": round(ema9.iloc[-1], 2),
            "EMA 21": round(ema21.iloc[-1], 2),
            "signal": sig
        }

    # Bollinger
    if "Bollinger Bands" in indicators:
        bb = ta.volatility.BollingerBands(data['Close'])
        upper = bb.bollinger_hband().iloc[-1]
        lower = bb.bollinger_lband().iloc[-1]
        price = data['Close'].iloc[-1]

        if price < lower:
            sig = "🟢 BUY"
            score += 1
        elif price > upper:
            sig = "🔴 SELL"
            score -= 1
        else:
            sig = "⚪ HOLD"

        indicator_output["Bollinger"] = {
            "Upper": round(upper, 2),
            "Lower": round(lower, 2),
            "signal": sig
        }

    # VWAP
    if "VWAP" in indicators:
        vwap = (data['Close'] * data['Volume']).cumsum() / data['Volume'].cumsum()
        val = vwap.iloc[-1]
        price = data['Close'].iloc[-1]

        if price > val:
            sig = "🟢 BUY"
            score += 1
        else:
            sig = "🔴 SELL"
            score -= 1

        indicator_output["VWAP"] = {
            "value": round(val, 2),
            "signal": sig
        }

    return score, float(data['Close'].iloc[-1]), indicator_output, data

# -------------------------
# RUN
# -------------------------
if st.button("Analyze"):

    st.write("⏳ Running Analysis...")

    market = detect_market(symbol)
    period, interval = get_interval(timeframe)

    data = get_data(symbol, period, interval)

    if data is None:
        st.error("❌ Data not available")
    else:
        score, price, ind_out, data = analyze(data, indicators)

        norm_score = score / len(indicators)

        if norm_score > 0.4:
            signal = "🚀 STRONG BUY"
        elif norm_score > 0.1:
            signal = "🟢 BUY"
        elif norm_score < -0.4:
            signal = "💥 STRONG SELL"
        elif norm_score < -0.1:
            signal = "🔴 SELL"
        else:
            signal = "⚪ HOLD"

        # TP/SL
        if market == "CRYPTO":
            tp_pct, sl_pct = 3, 1.5
        elif market == "FOREX":
            tp_pct, sl_pct = 1, 0.5
        else:
            tp_pct, sl_pct = 2, 1

        if "BUY" in signal:
            target = price * (1 + tp_pct / 100)
            stoploss = price * (1 - sl_pct / 100)
        elif "SELL" in signal:
            target = price * (1 - tp_pct / 100)
            stoploss = price * (1 + sl_pct / 100)
        else:
            target = price
            stoploss = price

        # Fibonacci
        recent = data.tail(50)
        high = recent['High'].max()
        low = recent['Low'].min()

        fib_38 = high - (high - low) * 0.382
        fib_50 = high - (high - low) * 0.5
        fib_61 = high - (high - low) * 0.618

        # OUTPUT
        st.subheader("📊 RESULT")

        col1, col2, col3 = st.columns(3)
        col1.metric("Market", market)
        col2.metric("Price", round(price, 2))
        col3.metric("Signal", signal)

        st.subheader("📈 Indicator Analysis")

        for name, val in ind_out.items():
            st.write(f"### {name}")
            st.json(val)

        st.subheader("🎯 Target & Stoploss")

        col4, col5 = st.columns(2)
        col4.metric("Target", round(target, 2))
        col5.metric("Stoploss", round(stoploss, 2))

        st.subheader("📐 Fibonacci")

        st.write({
            "38.2%": round(fib_38, 2),
            "50%": round(fib_50, 2),
            "61.8%": round(fib_61, 2)
        })

        with st.expander("📄 Show Raw Data"):
            st.dataframe(data.tail(20))