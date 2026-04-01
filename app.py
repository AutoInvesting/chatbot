import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 페이지 기본 설정
st.set_page_config(page_title="금 가격 괴리율 대시보드", layout="wide")
st.title("📈 한국 vs 국제 금 가격 괴리율 분석")

@st.cache_data # 데이터 로딩 속도 최적화를 위한 캐싱
def load_data():
    # 1. 국제 금 가격 (Gold Futures, GC=F) 및 원달러 환율 (KRW=X) 데이터 가져오기
    gold_intl = yf.download('GC=F', period='1y')['Close']
    krw_usd = yf.download('KRW=X', period='1y')['Close']
    
    # 데이터프레임 병합
    df = pd.concat([gold_intl, krw_usd], axis=1)
    df.columns = ['Intl_Gold_USD_oz', 'Exchange_Rate']
    df = df.dropna()
    
    # 2. 국제 금 가격을 원/g 단위로 변환 (1 troy ounce = 31.1034768 grams)
    df['Intl_Gold_KRW_g'] = (df['Intl_Gold_USD_oz'] * df['Exchange_Rate']) / 31.1034768
    
    # 3. 한국 금 가격 (가상 데이터: 국제 가격에 1%~3% 프리미엄 추가)
    # [주의] 이 부분은 추후 한국거래소(KRX)나 한국금거래소 크롤링 데이터로 교체하세요!
    np.random.seed(42)
    premium = np.random.uniform(1.01, 1.03, len(df))
    df['Korea_Gold_KRW_g'] = df['Intl_Gold_KRW_g'] * premium
    
    # 4. 괴리율 계산 (%)
    df['Disparity_Rate'] = ((df['Korea_Gold_KRW_g'] - df['Intl_Gold_KRW_g']) / df['Intl_Gold_KRW_g']) * 100
    
    return df

# 데이터 로드
df = load_data()

# 최신 괴리율 지표 보여주기
latest_disparity = df['Disparity_Rate'].iloc[-1]
st.metric(label="현재 김치 프리미엄(괴리율)", value=f"{latest_disparity:.2f}%")

# Plotly를 이용한 반응형 콤보 차트 생성
fig = make_subplots(specs=[[{"secondary_y": True}]])

# 왼쪽 Y축: 금 가격
fig.add_trace(
    go.Scatter(x=df.index, y=df['Korea_Gold_KRW_g'], name="한국 금 가격 (원/g)", line=dict(color='red')),
    secondary_y=False,
)
fig.add_trace(
    go.Scatter(x=df.index, y=df['Intl_Gold_KRW_g'], name="국제 금 가격 (원/g)", line=dict(color='blue', dash='dot')),
    secondary_y=False,
)

# 오른쪽 Y축: 괴리율 (막대 그래프)
fig.add_trace(
    go.Bar(x=df.index, y=df['Disparity_Rate'], name="괴리율 (%)", opacity=0.3, marker_color='orange'),
    secondary_y=True,
)

# 차트 레이아웃 설정
fig.update_layout(
    title_text="최근 1년 한국/국제 금 가격 및 괴리율 추이",
    hovermode="x unified"
)
fig.update_yaxes(title_text="가격 (원/g)", secondary_y=False)
fig.update_yaxes(title_text="괴리율 (%)", secondary_y=True)

# Streamlit에 차트 그리기
st.plotly_chart(fig, use_container_width=True)

# 데이터프레임 표기 (옵션)
with st.expander("상세 데이터 보기"):
    st.dataframe(df.tail(10))
