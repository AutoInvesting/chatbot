import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 페이지 기본 설정
st.set_page_config(page_title="금 가격 괴리율 대시보드", layout="wide")
st.title("📈 한국 vs 국제 금 가격 괴리율 분석")

@st.cache_data
def load_data():
    # 1. 국제 금 가격 (GC=F) 및 원달러 환율 (KRW=X) 데이터 가져오기
    # 데이터가 없을 경우를 대비해 기간을 조금 넉넉히 잡습니다.
    gold_intl = yf.download('GC=F', period='1y')['Close']
    krw_usd = yf.download('KRW=X', period='1y')['Close']
    
    # 데이터프레임 병합
    df = pd.concat([gold_intl, krw_usd], axis=1)
    df.columns = ['Intl_Gold_USD_oz', 'Exchange_Rate']
    
    # 데이터가 비어있는 행 제거
    df = df.dropna()
    
    if len(df) > 0:
        # 2. 국제 금 가격을 원/g 단위로 변환 (1 troy ounce = 31.1034768 grams)
        df['Intl_Gold_KRW_g'] = (df['Intl_Gold_USD_oz'] * df['Exchange_Rate']) / 31.1034768
        
        # 3. 한국 금 가격 (가상 데이터: 실제 연동 전까지 임시 사용)
        np.random.seed(42)
        premium = np.random.uniform(1.01, 1.03, len(df))
        df['Korea_Gold_KRW_g'] = df['Intl_Gold_KRW_g'] * premium
        
        # 4. 괴리율 계산 (%)
        df['Disparity_Rate'] = ((df['Korea_Gold_KRW_g'] - df['Intl_Gold_KRW_g']) / df['Intl_Gold_KRW_g']) * 100
        
    return df

# 데이터 로드
df = load_data()

# 데이터가 있는지 확인 후 출력
if not df.empty:
    # 최신 괴리율 지표
    latest_disparity = df['Disparity_Rate'].iloc[-1]
    st.metric(label="현재 김치 프리미엄(가상 괴리율)", value=f"{latest_disparity:.2f}%")

    # 차트 생성 로직
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Scatter(x=df.index, y=df['Korea_Gold_KRW_g'], name="한국 금 가격 (원/g)", line=dict(color='red')), secondary_y=False)
    fig.add_trace(go.Scatter(x=df.index, y=df['Intl_Gold_KRW_g'], name="국제 금 가격 (원/g)", line=dict(color='blue', dash='dot')), secondary_y=False)
    fig.add_trace(go.Bar(x=df.index, y=df['Disparity_Rate'], name="괴리율 (%)", opacity=0.3, marker_color='orange'), secondary_y=True)

    fig.update_layout(title_text="최근 1년 한국/국제 금 가격 및 괴리율 추이", hovermode="x unified")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.error("데이터를 불러오지 못했습니다. 잠시 후 다시 시도하거나 인터넷 연결을 확인해주세요.")
