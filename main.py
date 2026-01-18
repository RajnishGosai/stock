import streamlit as st
import yfinance as yf
import pandas_ta as ta
import pandas as pd
import datetime

# --- SETTINGS & UI ---
st.set_page_config(page_title="Intraday Sniper", layout="wide")
st.title("⚡ Intraday Sniper: Auto-Scanner")
st.markdown("Scanning for **Momentum**, **VWAP Breakouts**, and **Risk-Adjusted Exits**.")

# 1. STABLE TICKER FETCHING
@st.cache_data
def get_nifty50_tickers():
    try:
        # Reliable URL for Nifty 50 list
        url = "https://www.niftyindices.com/IndexConstituent/ind_nifty50list.csv"
        df = pd.read_csv(url)
        return [f"{s}.NS" for s in df['Symbol'].tolist()]
    except:
        # Fallback if NSE website is blocking requests
        return ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS", 
                "TATAMOTORS.NS", "SBIN.NS", "BHARTIARTL.NS", "ITC.NS", "LT.NS"]

# 2. ANALYSIS ENGINE
def analyze_stock(symbol):
    try:
        # Download 1-minute data for the current session
        df = yf.download(symbol, period="1d", interval="1m", progress=False)
        if df.empty or len(df) < 20: return None

        # Technical Indicators
        df['VWAP'] = ta.vwap(df['High'], df['Low'], df['Close'], df['Volume'])
        df['RSI'] = ta.rsi(df['Close'], length=14)
        df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)

        last = df.iloc[-1]
        price = round(last['Close'], 2)
        vwap = round(last['VWAP'], 2)
        rsi = round(last['RSI'], 1)
        atr = last['ATR']

        # CRITERIA: Price above VWAP and RSI > 60
        if price > vwap and rsi > 60:
            # Risk Management: 1.5x ATR Stop Loss
            sl = round(price - (1.5 * atr), 2)
            risk = price - sl
            target = round(price + (2 * risk), 2) # 1:2 Reward/Risk
            
            return {
                "Ticker": symbol,
                "Price": price,
                "VWAP": vwap,
                "RSI": rsi,
                "Signal": "🚀 BULLISH",
                "Stop Loss": sl,
                "Target": target
            }
        return None
    except:
        return None

# 3. SIDEBAR CONTROLS
st.sidebar.header("Scanner Settings")
budget = st.sidebar.number_input("Trading Budget (₹)", value=50000)
max_risk_per_trade = st.sidebar.slider("Risk Per Trade (%)", 0.5, 2.0, 1.0) / 100

# 4. EXECUTION
if st.button("🔍 START SCAN"):
    tickers = get_nifty50_tickers()
    st.info(f"Scanning {len(tickers)} liquid stocks...")
    
    results = []
    progress_bar = st.progress(0)
    
    for i, t in enumerate(tickers):
        res = analyze_stock(t)
        if res:
            # Position Sizing: How many shares to buy?
            risk_amt = budget * max_risk_per_trade
            loss_per_share = res['Price'] - res['Stop Loss']
            if loss_per_share > 0:
                res['Qty'] = int(risk_amt // loss_per_share)
            else:
                res['Qty'] = 0
            results.append(res)
        progress_bar.progress((i + 1) / len(tickers))
    
    if results:
        df_results = pd.DataFrame(results)
        st.success(f"Found {len(results)} Opportunities!")
        
        # Display as nice Cards
        for idx, row in df_results.iterrows():
            with st.container():
                col1, col2, col3, col4 = st.columns(4)
                col1.metric(row['Ticker'], f"₹{row['Price']}")
                col2.metric("Target", f"₹{row['Target']}", delta="Exit High")
                col3.metric("Stop Loss", f"₹{row['Stop Loss']}", delta="-1.5x ATR", delta_color="inverse")
                col4.metric("Quantity", row['Qty'], delta="Based on Risk")
                st.divider()
        
        st.dataframe(df_results)
    else:
        st.warning("No high-momentum setups found. Try again in 10 minutes.")
