import streamlit as st
import yfinance as yf
import pandas as pd
import requests
from bs4 import BeautifulSoup
import plotly.graph_objects as go
from datetime import datetime

# 1. 페이지 설정
st.set_page_config(page_title="Quant Dashboard", layout="wide")

# --- 핵심 데이터 함수 ---

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
        if g.empty or x.empty: return pd.DataFrame()
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
        curr = d.iloc[-1]
        s = (12*(curr/d.iloc[-21]-1)) + (4*(curr/d.iloc[-63]-1)) + (2*(curr/d.iloc[-126]-1)) + (1*(curr/d.iloc[-252]-1))
        return float(s)
    except:
        return -999.0

# --- 메인 화면 구성 ---
st.title("💰 Quant & Gold Dashboard")
st.write(f"Update: {datetime.now().strftime('%Y-%m-%d')}")

# 섹션 1: 금 시세 분석
with st.expander("Gold Analysis", expanded=True):
    kr = get_gold()
    df_g = load_data()
    if kr and not df_g.empty:
        intl = df_g['KRW_g'].iloc[-1]
        gap = ((kr - intl) / intl) * 100
        c1, c2, c3 = st.columns(3)
        c1.metric("Korea Gold", f"{kr:,.0f}원")
        c2.metric("Intl Gold", f"{intl:,.0f}원")
        c3.metric("Gap (%)", f"{gap:.2f}%")
        fig = go.Figure(go.Scatter(x=df_g.index, y=df_g['KRW_g'], name='Price'))
        fig.update_layout(height=300, margin=dict(l=0,r=0,t=0,b=0))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.write("금 데이터를 불러오는 중입니다...")

st.divider()

# 섹션 2: 3대 전략 리밸런싱
st.subheader("📬 Monthly Rebalancing Signals")
col1, col2, col3 = st.columns(3)

with st.spinner('Calculating Strategy Signals...'):
    # 1. BAA 전략
    with col1:
        st.info("### 1. BAA Strategy")
        v_s = get_score('VWO')
        b_s = get_score('BND')
        if v_s > 0 and b_s > 0:
            ast = ['QQQ', 'SPY', 'IWM', 'VGK', 'EWJ', 'VWO', 'GLD', 'DBC']
            res_dict = {t: get_score(t) for t in ast}
            best_ticker = max(res_dict, key=res_dict.get)
            st.error("MODE: Aggressive 🔥")
            st.markdown(f"## Buy: {best_ticker}")
        else:
            ast = ['BIL', 'IEF', 'TIP']
            res_dict = {t: get_score(t) for t in ast}
            best_ticker = max(res_dict, key=res_dict.get)
            st.success("MODE: Protective 🛡️")
            st.markdown(f"## Buy: {best_ticker}")

    # 2. 채권 동적 배분
    with col2:
        st.info("### 2. Bond Dynamic")
        b_list = ['TLT', 'IEF', 'SHY', 'LQD', 'TIP']
        b_res = {t: get_score(t) for t in b_list}
        b_best = max(b_res, key=b_res.get)
        st.success("MODE: Rotation 📈")
        st.markdown(f"## Buy: {b_best}")

    # 3. 변형 듀얼 모멘텀
    with col3:
        st.info("### 3. Dual Momentum")
        try:
            d_data = {}
            for t in ['SPY', 'EFA', 'BIL']:
                px = yf.download(t, period='13m')['Close']
                if not px.empty:
                    d_data[t] = (px.iloc[-1] / px.iloc[0]) - 1
                else:
                    d_data[t] = -999.0
            
            winner = 'SPY' if d_data['SPY'] > d_data['EFA'] else 'EFA'
            if d_data[winner] < d_data['BIL'] or d_data[winner] < 0:
                st.success("MODE: Risk-Off 💤")
                st.markdown("## Buy: BIL")
            else:
                st.error("MODE: Risk-On 🚀")
                st.markdown(f"## Buy: {winner}")
        except:
            st.write("데이터를 계산할 수 없습니다.")

st.divider()
st.caption("제공되는 데이터는 야후 파이낸스 기반이며, 투자 책임은 본인에게 있습니다.")
