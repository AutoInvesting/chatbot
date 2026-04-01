import streamlit as st
import yfinance as yf
import pandas as pd
import requests
from bs4 import BeautifulSoup
import plotly.graph_objects as go
from datetime import datetime

# 1. 페이지 설정
st.set_page_config(page_title="Quant Tax-Free Dashboard", layout="wide")

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
        # 13612 모멘텀 스코어 공식
        s = (12*(curr/d.iloc[-21]-1)) + (4*(curr/d.iloc[-63]-1)) + (2*(curr/d.iloc[-126]-1)) + (1*(curr/d.iloc[-252]-1))
        return float(s)
    except:
        return -999.0

# --- 메인 화면 ---
st.title("💰 Tax-Free Quant Dashboard")
st.write(f"최종 업데이트: {datetime.now().strftime('%Y-%m-%d')}")

# 섹션 1: 금 시세
with st.expander("Gold Analysis", expanded=True):
    kr = get_gold()
    df_g = load_data()
    if kr and not df_g.empty:
        intl = df_g['KRW_g'].iloc[-1]
        gap = ((kr - intl) / intl) * 100
        c1, c2, c3 = st.columns(3)
        c1.metric("국내 금 시세", f"{kr:,.0f}원")
        c2.metric("국제 환산가", f"{intl:,.0f}원")
        c3.metric("괴리율(Gap)", f"{gap:.2f}%")
        fig = go.Figure(go.Scatter(x=df_g.index, y=df_g['KRW_g'], name='Price'))
        fig.update_layout(height=300, margin=dict(l=0,r=0,t=0,b=0))
        st.plotly_chart(fig, use_container_width=True)

st.divider()

# 섹션 2: 3대 전략 (PTP 종목 제외 완료)
st.subheader("📬 월간 리밸런싱 신호 (No-PTP Ver.)")
col1, col2, col3 = st.columns(3)

with st.spinner('계산 중...'):
    # 1. BAA 전략 (공격형 유니버스 수정)
    with col1:
        st.info("### 1. BAA 공격형")
        # 카나리아 지표 (보수적 접근: 둘 다 0보다 커야 함)
        if get_score('VWO') > 0 and get_score('BND') > 0:
            # DBC(PTP) -> PDBC(No-PTP)로 교체 / GLD 등 안전 종목 위주
            ast = ['QQQ', 'SPY', 'IWM', 'VGK', 'EWJ', 'VWO', 'GLD', 'PDBC'] 
            res = {t: get_score(t) for t in ast}
            best = max(res, key=res.get)
            st.error("모드: 공격 🔥")
            st.markdown(f"## 추천: {best}")
        else:
            # 수비 자산
            ast = ['BIL', 'IEF', 'TIP']
            res = {t: get_score(t) for t in ast}
            best = max(res, key=res.get)
            st.success("모드: 수비 🛡️")
            st.markdown(f"## 추천: {best}")

    # 2. 채권 동적 배분
    with col2:
        st.info("### 2. 채권 동적 배분")
        # PTP 이슈 없는 채권 ETF들
        b_ast = ['TLT', 'IEF', 'SHY', 'LQD', 'TIP']
        b_res = {t: get_score(t) for t in b_ast}
        b_best = max(b_res, key=b_res.get)
        st.success("모드: 로테이션 📈")
        st.markdown(f"## 추천: {b_best}")

    # 3. 변형 듀얼 모멘텀
    with col3:
        st.info("### 3. 변형 듀얼 모멘텀")
        try:
            d_s = {}
            for t in ['SPY', 'EFA', 'BIL']:
                px = yf.download(t, period='13m')['Close']
                d_s[t] = (px.iloc[-1] / px.iloc[0]) - 1 if not px.empty else -999.0
            
            # 상대 모멘텀 승자 결정
            win = 'SPY' if d_s['SPY'] > d_s['EFA'] else 'EFA'
            # 절대 모멘텀(0 혹은 BIL보다 높아야 함)
            if d_s[win] < d_s['BIL'] or d_s[win] < 0:
                st.success("모드: 현금 대기 💤")
                st.markdown("## 추천: BIL")
            else:
                st.error("모드: 주식 보유 🚀")
                st.markdown(f"## 추천: {win}")
        except:
            st.write("데이터 오류")

st.divider()
st.caption("⚠️ DBC 등 PTP 세금 이슈 종목은 유니버스에서 제외되었습니다. (PDBC로 대체)")
