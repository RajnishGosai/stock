import streamlit as st
import yfinance as yf
import pandas_ta as ta
import pandas as pd
import io
import requests

st.set_page_config(page_title="F&O Intraday Sniper", layout="wide")
st.title("🏹 All F&O Stock Sniper")

# 1. FETCH ALL F&O SYMBOLS (Dynamic)
@st.cache_data
def get_all_fno_stocks():
    try:
        # Using Zerodha's public instrument list as a reliable source for F&O
        url = "https://api.kite.trade/instruments"
        response = requests.get(url).text
        df = pd.read_csv(io.StringIO(response))
        
        # Filter for NFO (National Futures & Options) segment and specifically Futures
        # This gives us the underlying equity symbols for all F&O stocks
        fno_df = df[df['exchange'] == 'NFO']
        fno_list = fno_df['name'].unique().tolist()
        
        # Format for Yahoo Finance (.NS suffix)
        # We filter out the indices like NIFTY/BANKNIFTY to focus on stocks
        exclude = ['NIFTY', 'BANKNIFTY', 'FINNIFTY', 'MIDCPNIFTY']
        final_list = [f"{s}.NS" for s in fno_list if s not in exclude and isinstance(s, str)]
        
        return sorted(final_list)
    except Exception as e:
        st.error(f"Error fetching F&O list: {e}")
        return ["RELIANCE.NS", "SBIN.NS", "TATASTEEL.NS"] # Minimal fallback

# 2. THE SCANNER ENGINE
def scan_logic(symbol):
    try:
        df = yf.download(symbol, period="1d", interval="1m", progress=False)
        if df.empty or len(df) < 20: return None
        
        # Technical Logic
        df['VWAP'] = ta.vwap(df['High'], df['Low'], df['Close'], df['Volume'])
        df['RSI'] = ta.rsi(df['Close'], length=14)
        df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
        
        last = df.iloc[-1]
        price = last['Close']
        
        # Strategy: Price > VWAP (Bullish) and RSI > 60 (Strength)
        if price > last['VWAP'] and last['RSI'] > 60:
            sl = round(price - (1.5 * last['ATR']), 2)
            target = round(price + (2 * (price - sl)), 2)
            return {
                "Ticker": symbol, "Price": round(price, 2), "RSI": round(last['RSI'], 1),
                "StopLoss": sl, "Target": target, "Status": "🔥 STRONG BUY"
            }
    except: return None

# 3. UI DASHBOARD
if st.button("🚀 SCAN ALL F&O STOCKS"):
    fno_universe = get_all_fno_stocks()
    st.info(f"Scanning {len(fno_universe)} F&O stocks in real-time...")
    
    results = []
    prog = st.progress(0)
    for i, ticker in enumerate(fno_universe):
        res = scan_logic(ticker)
        if res: results.append(res)
        prog.progress((i + 1) / len(fno_universe))
        
    if results:
        res_df = pd.DataFrame(results)
        st.success(f"Found {len(results)} high-momentum F&O setups!")
        st.dataframe(res_df, use_container_width=True)
    else:
        st.warning("No F&O stocks currently meet the criteria. Try again shortly.")
