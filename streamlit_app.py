import streamlit as st
import yfinance as yf
import pandas as pd
import requests
from bs4 import BeautifulSoup
import plotly.graph_objects as go
from datetime import datetime

# 1. 페이지 설정
st.set_page_config(page_title="퀀트 투자 통합 대시보드", layout="wide")

# --- 데이터 로직 함수들 ---

def get_korea_gold():
    try:
        url = "https://finance.naver.com/marketindex/goldDetail.naver"
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        soup = BeautifulSoup(res.text, 'html.parser')
        price_text = soup.select_one('.value').text
        return float(price_text.replace(',', ''))
    except:
        return None

@st.cache_data(ttl=3600)
def load_intl_gold_data():
    try:
        gold = yf.download('GC=F', period='1y')['Close']
        fx = yf.download('KRW=X', period='1y')['Close']
        df = pd.concat([gold, fx], axis=1).dropna()
        df.columns = ['USD_oz', 'FX']
        df['Intl_KRW_g'] = (df['USD_oz'] * df['FX']) / 31.1034768
        return df
    except:
        return pd.DataFrame()

def get_13612_score(ticker):
    try:
        data = yf.download(ticker, period='14m')['Close']
        if len(data) < 252: return -999.0
        curr = data.iloc[-1]
        m1, m3, m6, m12 = data.iloc[-21], data.iloc[-63], data.iloc[-126], data.iloc[-252]
        score = (12 * (curr/m1 - 1)) + (4 * (curr/m3 - 1)) + (2 * (curr/m6 - 1)) + (1 * (curr/m12 - 1))
        return float(score)
    except:
        return -999.0

def get_dual_momentum_signal():
    try:
        tickers = ['SPY', 'EFA', 'BIL']
        scores = {}
        for t in tickers:
            data = yf.download(t, period='13m')['Close']
            ret_12m = (data.iloc[-1] / data.iloc[0]) - 1
            scores[t] = float(ret_12m)
        
        winner = 'SPY' if scores['SPY'] > scores['EFA'] else 'EFA'
        if scores[winner] < scores['BIL'] or scores[winner] < 0:
            return "현금 대피 (BIL)", "blue"
        return winner, "red"
    except:
        return "데이터 오류", "gray"

# --- 메인 화면 ---
st.title("🚀 퀀트 투자 통합 리밸런싱 대시보드")
st.write(f"최근 업데이트: {datetime.now().strftime('%Y-%m-%d')}")

# 섹션 1: 금 시세
with st.expander("🟡 국내/국제 금 시세 및 괴리율 확인", expanded=True):
    kr_gold = get_korea_gold()
    df_intl = load_intl_gold_data()
    if kr_gold and not df_intl.empty:
        intl_gold = df_intl['Intl_KRW_g'].iloc[-1]
        gap = ((kr_gold - intl_gold) / intl_gold) * 100
        c1, c2, c3 = st.columns(3)
        c1.metric("국내 금값", f"{kr_gold:,.0f}원")
        c2.metric("국제 환산가", f"{intl_gold:,.0f}원")
        c3.metric("괴리율", f"{gap:.2f}%")
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df_intl.index, y=df_intl['Intl_KRW_g'], name='국제 금값(원/g)'))
        fig.update_layout(height=300, margin=dict(l=0,r=0,t=0,b=0))
        st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# 섹션 2: 3대 전략 리밸런싱 신호
st.subheader("📬 이번 달 전략별 매수 신호")
col_baa, col_bond, col_dual = st.columns(3)

with st.spinner('전략 계산 중...'):
    # 1. 공격형 BAA
    with col_baa:
        st.info("### 1. 공격형 BAA")
        canary = all(get_13612_score(t) > 0 for t in ['VWO', 'BND'])
        if canary:
            agg_assets = ['QQQ', 'SPY', 'IWM', 'VGK', 'EWJ', 'VWO', 'GLD', 'DBC']
            scores = {t: get_13612_score(t) for t in agg_assets}
            best = max(scores, key=scores.get)
            st.error(f"**모드: 공격 🔥**\n\n# {best}")
        else:
            prot_assets = ['BIL', 'IEF', 'TIP']
            scores = {t: get_13612_score(t) for t in prot_assets}
            best = max(scores, key=scores.get)
            st.info(f"**모드: 수비 🛡️**\
