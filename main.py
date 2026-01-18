import streamlit as st
import yfinance as yf
import pandas_ta as ta
import pandas as pd
import requests
import io

# --- APP CONFIGURATION ---
st.set_page_config(page_title="Intraday Sniper", layout="wide")
st.title("⚡ Intraday Sniper: Auto-Scanner")

# 1. ROBUST TICKER FETCHING (Fixed)
@st.cache_data
def get_nifty50_tickers():
    # Official NSE CSV URL
    url = "https://www.niftyindices.com/IndexConstituent/ind_nifty50list.csv"
    
    # Custom headers to prevent blocking
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            df = pd.read_csv(io.StringIO(response.text))
            # Convert to Yahoo Finance format
            return [f"{s.strip()}.NS" for s in df['Symbol'].tolist()]
        else:
            raise Exception("URL blocked")
    except Exception as e:
        st.sidebar.warning("Live list unreachable. Using stable fallback list.")
        # Fallback: Top 20 most liquid Nifty 50 stocks
        return [
            "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "ICICIBANK.NS", "INFY.NS", 
            "SBIN.NS", "BHARTIARTL.NS", "ITC.NS", "LT.NS", "BAJFINANCE.NS",
            "AXISBANK.NS", "ADANIENT.NS", "SUNPHARMA.NS", "TITAN.NS", "TATAMOTORS.NS",
            "NTPC.NS", "M&M.NS", "POWERGRID.NS", "ASIANPAINT.NS", "HCLTECH.NS"
        ]

# 2. ANALYSIS ENGINE
def analyze_stock(symbol):
    try:
        # Pull 1-minute data for the current day
        df = yf.download(symbol, period="1d", interval="1m", progress=False)
        if df.empty or len(df) < 20: return None

        # INDICATORS
        # VWAP requires High, Low, Close, and Volume
        df['VWAP'] = ta.vwap(df['High'], df['Low'], df['Close'], df['Volume'])
        df['RSI'] = ta.rsi(df['Close'], length=14)
        df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)

        last = df.iloc[-1]
        price = round(last['Close'], 2)
        vwap = round(last['VWAP'], 2)
        rsi = round(last['RSI'], 1)
        atr = last['ATR']

        # CRITERIA: Buy if Price > VWAP and RSI > 60
        if price > vwap and rsi > 60:
            # Stop Loss at 1.5x ATR below entry
            sl = round(price - (1.5 * atr), 2)
            # Target for 1:2 Risk-Reward
            target = round(price + (2 * (price - sl)), 2)
            
            return {
                "Ticker": symbol, "Price": price, "Signal": "🚀 BUY",
                "Stop Loss": sl, "Target": target, "RSI": rsi, "Volume": int(last['Volume'])
            }
        return None
    except:
        return None

# 3. UI CONTROLS
st.sidebar.header("Trading Budget")
user_budget = st.sidebar.number_input("Total Capital (₹)", value=100000)
risk_pct = st.sidebar.slider("Risk Per Trade (%)", 0.5, 2.0, 1.0) / 100

if st.button("🔍 START LIVE SCAN"):
    tickers = get_nifty50_tickers()
    st.write(f"Scanning {len(tickers)} Stocks...")
    
    found_any = False
    progress_bar = st.progress(0)
    
    results = []
    for i, t in enumerate(tickers):
        res = analyze_stock(t)
        if res:
            # Position Sizing
            risk_amt = user_budget * risk_pct
            qty = int(risk_amt // (res['Price'] - res['Stop Loss'])) if (res['Price'] - res['Stop Loss']) > 0 else 0
            res['Quantity'] = qty
            results.append(res)
            found_any = True
        progress_bar.progress((i + 1) / len(tickers))
    
    if found_any:
        df_final = pd.DataFrame(results)
        st.success("High Probability Setups Found!")
        
        # Display as cards
        for item in results:
            with st.expander(f"🎯 {item['Ticker']} - {item['Signal']}"):
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Entry", f"₹{item['Price']}")
                c2.metric("Target", f"₹{item['Target']}")
                c3.metric("Stop Loss", f"₹{item['Stop Loss']}")
                c4.metric("Buy Qty", item['Quantity'])
        
        st.table(df_final[['Ticker', 'Price', 'Signal', 'RSI', 'Quantity']])
    else:
        st.warning("No stocks currently match the VWAP + RSI criteria.")
