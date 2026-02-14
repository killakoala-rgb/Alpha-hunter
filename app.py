import streamlit as st
from polygon import RESTClient
from datetime import datetime, timedelta
from openai import OpenAI
import pandas as pd

st.set_page_config(page_title="Alpha Hunter", page_icon="🦍", layout="centered")

st.title("🦍 ALPHA HUNTER")
st.caption("Live Options Profit Scanner • Built for Phone")

with st.sidebar:
    st.header("🔑 API Keys")
    polygon_key = st.text_input("Polygon.io Key", type="password", value=st.secrets.get("POLYGON_KEY", ""))
    openai_key = st.text_input("OpenAI Key", type="password", value=st.secrets.get("OPENAI_KEY", ""))
    if st.button("💾 Save Keys"):
        st.session_state.polygon_key = polygon_key
        st.session_state.openai_key = openai_key
        st.success("Keys saved! Run scan below.")

WATCHLIST = ["TSLA", "NVDA", "PLTR", "RIVN", "AMD", "SMCI", "AAPL", "META", "HOOD", "COIN"]

if 'polygon_key' in st.session_state and st.session_state.polygon_key:
    client = RESTClient(st.session_state.polygon_key)
    llm = OpenAI(api_key=st.session_state.openai_key)

    if st.button("🚀 RUN NUCLEAR SCAN", type="primary", use_container_width=True):
        with st.spinner("Scanning market for 10x setups..."):
            results = []
            for ticker in WATCHLIST:
                try:
                    price = client.get_last_trade(ticker).price
                    
                    fin = list(client.list_stock_financials(ticker, limit=2))
                    fundamentals = [f"{f.fiscal_period} {f.fiscal_year}: Rev ${getattr(f.financials.income_statement.revenues, 'value', 0)/1e9:.1f}B" for f in fin]
                    
                    news = [n.title[:80] for n in list(client.list_ticker_news(ticker, limit=5))]
                    
                    today = datetime.now().date()
                    opts = list(client.list_options_contracts(
                        underlying_ticker=ticker, contract_type="call",
                        expiration_date_gte=(today + timedelta(days=30)).isoformat(),
                        expiration_date_lte=(today + timedelta(days=90)).isoformat(),
                        limit=20
                    ))
                    calls = [f"{o.expiration_date} ${o.strike_price}" for o in opts[:8]]
                    
                    prompt = f"""Savage options trader mode. BUY CALLS only.
                    {ticker} @ ${price}
                    Fundamentals: {fundamentals}
                    News: {news[:4]}
                    Calls: {calls[:5]}
                    
                    JSON only: {{"verdict": "STRONG BUY/BUY/HOLD/SKIP", "top_call": "Apr 17 450", "why": "2 sentences", "score": 92}}"""
                    
                    resp = llm.chat.completions.create(model="gpt-4o-mini", messages=[{"role":"user","content":prompt}], temperature=0.3)
                    v = eval(resp.choices[0].message.content)
                    
                    results.append({
                        "Ticker": ticker,
                        "Price": f"${price:.2f}",
                        "Signal": v.get("verdict", "BUY"),
                        "Best Call": v.get("top_call", "N/A"),
                        "Score": v.get("score", 0),
                        "Why": v.get("why", "")[:110]
                    })
                except:
                    pass
            
            df = pd.DataFrame(results)
            df = df.sort_values("Score", ascending=False)
            st.dataframe(df.style.highlight_max(subset=["Score"], color="lightgreen"), use_container_width=True, hide_index=True)
            st.balloons()
else:
    st.info("Enter your API keys in the sidebar to unlock the hunter.")
