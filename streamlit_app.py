import streamlit as st
import yfinance as yf
import pandas as pd
import requests
from bs4 import BeautifulSoup
import plotly.graph_objects as go
from datetime import datetime

# 1. 페이지 설정
st.set_page_config(page_title="Quant Dashboard", layout="wide")

# --- 핵심 함수 정의 ---

def get_gold():
    try:
        url = "https://finance.naver.com/marketindex/goldDetail.naver"
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        soup = BeautifulSoup(res.text, 'html.parser')
        val = soup.select_one('.value').text
        return float(val.replace(',', ''))
    except:
        return None

@st.cache_data(ttl=3600)
def load_data():
    try:
        g = yf.download('GC=F', period='1y')['Close']
        x = yf.download('KRW=X', period='1y')['Close']
        df = pd.concat([g, x], axis=1).dropna()
        df.columns = ['USD', 'FX']
        df['KRW_g'] = (df['USD'] * df['FX']) / 31.1034768
        return df
    except:
        return pd.DataFrame()

def get_score(ticker):
    try:
        d = yf.download(ticker, period='14m')['Close']
        if len(d) < 252: return -999.0
        c = d.iloc[-1]
        # 13612 모멘텀 스코어 공식
        s = (12*(c/d.iloc[-21]-1)) + (4*(c/d.iloc[-63]-1)) + (2*(c/d.iloc[-126]-1)) + (1*(c/d.iloc[-252]-1))
        return float(s)
    except:
        return -999.0

# --- 화면 구성 ---
st.title("💰 Quant & Gold Dashboard")
st.write(f"Update: {datetime.now().strftime('%Y-%m-%d')}")

# 섹션 1: 금 시세
with st.expander("Gold Analysis", expanded=True):
    kr = get_gold()
    df = load_data()
    if kr and not df.empty:
        intl = df['KRW_g'].iloc[-1]
        gap = ((kr - intl) / intl) * 100
        c1, c2, c3 = st.columns(3)
        c1.metric("Korea Gold", f"{kr:,.0f}원")
        c2.metric("Intl Gold", f"{intl:,.0f}원")
        c3.metric("Gap (%)", f"{gap:.2f}%")
        fig = go.Figure(go.Scatter(x=df.index, y=df['KRW_g'], name='Price'))
        fig.update_layout(height=300, margin=dict(l=0,r=0,t=0,b=0))
        st.plotly_chart(fig, use_container_width=True)

st.divider()

# 섹션 2: 3대 전략 리밸런싱
st.subheader("📬 Monthly Rebalancing Signals")
col1, col2, col3 = st.columns(3)

with st.spinner('Calculating...'):
    # 1. BAA 전략
    with col1:
        st.info("### 1. BAA")
        vwo_s = get_score('VWO')
        bnd_s = get_score('BND')
        if vwo_s > 0 and bnd_s > 0:
            ast = ['QQQ', 'SPY', 'IWM', 'VGK', 'EWJ', 'VWO', 'GLD', 'DBC']
            res = {t: get_score(t) for t in ast}
            best = max(res, key=res.get)
            st.error(f"MODE: Aggressive 🔥")
            st.markdown(f"## Buy: {best}")
        else:
            ast = ['BIL', 'IEF', 'TIP']
            res = {
