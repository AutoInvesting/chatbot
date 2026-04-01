import streamlit as st
import yfinance as yf
import pandas as pd
import requests
from bs4 import BeautifulSoup
import plotly.graph_objects as go
from datetime import datetime

# 1. 페이지 설정
st.set_page_config(page_title="Quant Multi-Strategy Dashboard", layout="wide")

# --- 데이터 로직 함수들 ---

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
        # 13612 모멘텀 스코어 공식
        s = (12*(curr/d.iloc[-21]-1)) + (4*(curr/d.iloc[-63]-1)) + (2*(curr/d.iloc[-126]-1)) + (1*(curr/d.iloc[-252]-1))
        return float(s)
    except:
        return -999.0

# --- 메인 화면 구성 ---
st.title("🚀 퀀트 자산배분 통합 대시보드")
st.write(f"최근 업데이트: {datetime.now().strftime('%Y-%m-%d')}")

# 섹션 1: 금 시세 분석 (유지)
with st.expander("🟡 실시간 금 시세 및 괴리율", expanded=True):
    kr = get_gold()
    df_g = load_data()
    if kr and not df_g.empty:
        intl = df_g['KRW_g'].iloc[-1]
        gap = ((kr - intl) / intl) * 100
        c1, c2, c3 = st.columns(3)
        c1.metric("국내 금값", f"{kr:,.0f}원")
        c2.metric("국제 환산가", f"{intl:,.0f}원")
        c3.metric("괴리율(Gap)", f"{gap:.2f}%")
        fig = go.Figure(go.Scatter(x=df_g.index, y=df_g['KRW_g'], name='Price'))
        fig.update_layout(height=300, margin=dict(l=0,r=0,t=0,b=0))
        st.plotly_chart(fig, use_container_width=True)

st.divider()

# 섹션 2: 4대 전략 리밸런싱 신호
st.subheader("📬 전략별 월간 리밸런싱 신호")
col1, col2, col3, col4 = st.columns(4)

with st.spinner('전략별 모멘텀 계산 중...'):
    # 공통 데이터 미리 계산
    v_s = get_score('VWO')
    b_s = get_score('BND')
    agg_assets = ['QQQ', 'SPY', 'IWM', 'VGK', 'EWJ', 'VWO', 'GLD', 'PDBC']
    def_assets = ['BIL', 'IEF', 'TIP']

    # 1. BAA 중도형 (기존 보수적 로직: AND)
    with col1:
        st.info("### 1. BAA 중도형")
        if v_s > 0 and b_s > 0:
            res = {t: get_score(t) for t in agg_assets}
            best = max(res, key=res.get)
            st.error("모드: 공격 🔥")
            st.markdown(f"## 추천: {best}")
        else:
            res = {t: get_score(t) for t in def_assets}
            best = max(res, key=res.get)
            st.success("모드: 수비 🛡️")
            st.markdown(f"## 추천: {best}")

    # 2. BAA 공격형 (강화된 로직: OR)
    with col2:
        st.info("### 2. BAA 공격형")
        if v_s > 0 or b_s > 0:
            res = {t: get_score(t) for t in agg_assets}
            best = max(res, key=res.get)
            st.error("모드: 공격 🔥")
            st.markdown(f"## 추천: {best}")
        else:
            res = {t: get_score(t) for t in def_assets}
            best = max(res, key=res.get)
            st.success("모드: 수비 🛡️")
            st.markdown(f"## 추천: {best}")

    # 3. 채권 동적 자산배분
    with col3:
        st.info("### 3. 채권 동적 배분")
        b_list = ['TLT', 'IEF', 'SHY', 'LQD', 'TIP']
        b_res = {t: get_score(t) for t in b_list}
        b_best = max(b_res, key=b_res.get)
        st.success("모드: 로테이션 📈")
        st.markdown(f"## 추천: {b_best}")

    # 4. 변형 듀얼 모멘텀
    with col4:
        st.info("### 4. 듀얼 모멘텀")
        try:
            d_data = {}
            for t in ['SPY', 'EFA', 'BIL']:
                px = yf.download(t, period='13m')['Close']
                d_data[t] = (px.iloc[-1] / px.iloc[0]) - 1 if not px.empty else -999.0
            
            winner = 'SPY' if d_data['SPY'] > d_data['EFA'] else 'EFA'
            if d_data[winner] < d_data['BIL'] or d_data[winner] < 0:
                st.success("모드: 현금 대기 💤")
                st.markdown("## 추천: BIL")
            else:
                st.error("모드: 주식 보유 🚀")
                st.markdown(f"## 추천: {winner}")
        except:
            st.write("데이터 오류")

st.divider()
st.caption("제공되는 모든 데이터는 PTP 세금 이슈 종목(DBC 등)을 배제하고 PDBC 등으로 대체된 '한국 투자자 친화적' 유니버스입니다.")
