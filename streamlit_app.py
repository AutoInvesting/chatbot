import streamlit as st
import yfinance as yf
import pandas as pd
import requests
from bs4 import BeautifulSoup
import plotly.graph_objects as go
from datetime import datetime, timedelta

# 1. 페이지 설정
st.set_page_config(page_title="퀀트 투자 & 금 시세 대시보드", layout="wide")

# --- 데이터 로드 함수들 ---

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
        df = pd.concat([gold, fx], axis=1)
        df.columns = ['USD_oz', 'FX']
        df = df.dropna()
        df['Intl_KRW_g'] = (df['USD_oz'] * df['FX']) / 31.1034768
        return df
    except:
        return pd.DataFrame()

# BAA 전략용 모멘텀 계산 함수
def get_momentum_score(ticker):
    data = yf.download(ticker, period='14m')['Close'] # 여유있게 14개월치
    if len(data) < 252: return -999
    
    # 현재가 및 과거 종가 (1, 3, 6, 12개월 전)
    curr = data.iloc[-1]
    m1 = data.iloc[-21] if len(data) > 21 else data.iloc[0]
    m3 = data.iloc[-63] if len(data) > 63 else data.iloc[0]
    m6 = data.iloc[-126] if len(data) > 126 else data.iloc[0]
    m12 = data.iloc[-252] if len(data) > 252 else data.iloc[0]
    
    # 13612 가중치 모멘텀 스코어 공식
    score = (12 * (curr/m1 - 1)) + (4 * (curr/m3 - 1)) + (2 * (curr/m6 - 1)) + (1 * (curr/m12 - 1))
    return score

# --- 메인 화면 시작 ---
st.title("📊 퀀트 자산배분 & 금 시세 대시보드")

# 1. 금 가격 섹션
kr_price = get_korea_gold()
df_intl = load_intl_gold_data()

if kr_price and not df_intl.empty:
    latest_intl = df_intl['Intl_KRW_g'].iloc[-1]
    disparity = ((kr_price - latest_intl) / latest_intl) * 100

    st.subheader("🟡 금 가격 및 괴리율")
    c1, c2, c3 = st.columns(3)
    c1.metric("국내 금값 (원/g)", f"{kr_price:,.0f}")
    c2.metric("국제 환산가 (원/g)", f"{latest_intl:,.0f}")
    c3.metric("오늘의 괴리율", f"{disparity:.2f}%")

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df_intl.index, y=df_intl['Intl_KRW_g'], name='국제 금 시세(원/g)'))
    fig.update_layout(title="최근 1년 국제 금 가격 추이", template="plotly_white", height=400)
    st.plotly_chart(fig, use_container_width=True)
    st.info(f"현재 괴리율은 {disparity:.2f}% 입니다.")

st.markdown("---")

# 2. 공격형 BAA 전략 섹션
st.subheader("🚀 공격형 BAA 이번 달 리밸런싱 신호")

with st.spinner('모멘텀 계산 중...'):
    # 자산군 정의
    canary = ['VWO', 'BND'] # 카나리아 자산 (신흥국 주식, 총합채권)
    aggressive = ['QQQ', 'SPY', 'IWM', 'VGK', 'EWJ', 'VWO', 'GLD', 'DBC'] # 공격 자산
    protective = ['BIL', 'IEF', 'TIP'] # 수비 자산

    # 카나리아 체크 (둘 다 스코어가 0보다 커야 공격 가능)
    canary_scores = {t: get_momentum_score(t) for t in canary}
    is_aggressive_mode = all(score > 0 for score in canary_scores.values())

    if is_aggressive_mode:
        # 공격 모드: 공격 자산 중 스코어 가장 높은 1개 선정
        agg_scores = {t: get_momentum_score(t) for t in aggressive}
        best_ticker = max(agg_scores, key=agg_scores.get)
        status_text = "🔥 공격 모드 (Aggressive)"
        recommend_ticker = best_ticker
        color = "red"
    else:
        # 수비 모드: 수비 자산 중 스코어 가장 높은 1개 선정
        prot_scores = {t: get_momentum_score(t) for t in protective}
        best_ticker = max(prot_scores, key=prot_scores.get)
        status_text = "🛡️ 수비 모드 (Protective)"
        recommend_ticker = best_ticker
        color = "blue"

    # 결과 표시
    res_col1, res_col2 = st.columns(2)
    with res_col1:
        st.write(f"### 현재 시장 상태: :{color}[{status_text}]")
        st.write(f"**카나리아 지표:** VWO({canary_scores['VWO']:.2f}), BND({canary_scores['BND']:.2f})")
    with res_col2:
        st.write("### 📢 이번 달 추천 종목")
        st.title(f"👉 :{color}[{recommend_ticker}]")

st.caption("※ BAA 전략은 매달 1일 리밸런싱을 원칙으로 하며, 위 수치는 야후 파이낸스 실시간 데이터를 기반으로 계산되었습니다.")
