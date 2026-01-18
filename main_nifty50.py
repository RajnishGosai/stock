import streamlit as st
import yfinance as yf
import pandas_ta as ta
import pandas as pd
import time

# --- 1. DYNAMIC STOCK LIST FETCHING ---
@st.cache_data
def get_liquid_universe():
    # Automatically get Nifty 50 tickers (Indian Market)
    # For US Market, you can use: tickers = pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')[0]['Symbol'].tolist()
    nifty50_url = "https://raw.githubusercontent.com/anirban-m/indian-stock-market-data/master/nifty50_list.csv"
    try:
        df = pd.read_csv(nifty50_url)
        return [f"{s}.NS" for s in df['Symbol'].tolist()]
    except:
        return ["RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS"]

# --- 2. LIVE SCANNER ENGINE ---
def analyze_market(tickers):
    opportunities = []
    progress_text = st.empty()
    
    for i, symbol in enumerate(tickers):
        progress_text.text(f"Scanning {i+1}/{len(tickers)}: {symbol}")
        try:
            # Fetch 1-minute interval data for the current day
            df = yf.download(symbol, period="1d", interval="1m", progress=False)
            if df.empty or len(df) < 20: continue

            # Technical Analysis
            df['VWAP'] = ta.vwap(df['High'], df['Low'], df['Close'], df['Volume'])
            df['RSI'] = ta.rsi(df['Close'], length=14)
            
            # Liquidity Filter: Avg Volume of last 10 minutes
            avg_vol = df['Volume'].tail(10).mean()
            last_price = df['Close'].iloc[-1]
            last_vwap = df['VWAP'].iloc[-1]
            last_rsi = df['RSI'].iloc[-1]

            # Strategy: Price > VWAP (Bullish) and RSI > 60 (Momentum)
            if last_price > last_vwap and last_rsi > 60:
                opportunities.append({
                    "Ticker": symbol,
                    "Price": round(last_price, 2),
                    "Signal": "🚀 BUY",
                    "RSI": round(last_rsi, 1),
                    "Vol (1m)": int(df['Volume'].iloc[-1])
                })
        except Exception:
            continue
    return pd.DataFrame(opportunities)

# --- 3. STREAMLIT UI ---
st.set_page_config(page_title="Auto-Intraday", layout="wide")
st.title("⚡ Auto-Liquid Stock Sniper")

if st.button("Start Real-Time Auto-Scan"):
    universe = get_liquid_universe()
    st.info(f"Scanning {len(universe)} high-liquidity stocks...")
    
    results = analyze_market(universe)
    
    if not results.empty:
        st.success("Found High-Probability Setups!")
        # Highlighting the Best Pick based on highest Volume
        best_pick = results.sort_values(by="Vol (1m)", ascending=False).iloc[0]
        
        st.metric(label="🏆 TOP PICK", value=best_pick['Ticker'], delta=f"Price: {best_pick['Price']}")
        st.dataframe(results, use_container_width=True)
    else:
        st.warning("No clear momentum detected. Try again in 5 minutes.")
