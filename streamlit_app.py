import streamlit as st
import yfinance as yf
import pandas as pd
import requests
from bs4 import BeautifulSoup
import plotly.graph_objects as go

# 페이지 설정
st.set_page_config(page_title="금 시세 괴리율 분석", layout="wide")

# 1. 네이버에서 오늘 한국 금 시세(원/g) 가져오기
def get_korea_gold_price():
    try:
        url = "https://finance.naver.com/marketindex/goldDetail.naver"
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        soup = BeautifulSoup(res.text, 'html.parser')
        price_text = soup.select_one('.value').text
        return float(price_text.replace(',', ''))
    except Exception as e:
        st.error(f"국내 가격 로드 실패: {e}")
        return None

# 2. 국제 데이터 로드 (금 선물 & 환율)
@st.cache_data(ttl=3600) # 1시간마다 캐시 갱신
def load_intl_data():
    # 금 선물(GC=F)과 환율(KRW=X) 최근 1년치
    gold = yf.download('GC=F', period='1y')['Close']
    fx = yf.download('KRW=X', period='1y')['Close']
    df = pd.concat([gold, fx], axis=1)
    df.columns = ['USD_oz', 'FX']
    df = df.dropna()
    # 국제 가격을 원/g으로 환산 (1oz = 31.1034768g)
    df['Intl_KRW_g'] = (df['USD_oz'] * df['FX']) / 31.1034768
    return df

# 실행
st.title("💰 국내/국제 금 시세 및 괴리율")

kr_price = get_korea_gold_price()
df_intl = load_intl_data()

if kr_price and not df_intl.empty:
    # 오늘의 국제 환산가 및 괴리율 계산
    latest_intl_price = df_intl['Intl_KRW_g'].iloc[-1]
    disparity = ((kr_price - latest_intl_price) / latest_intl_price) * 100

    # 상단 지표 레이아웃
    col1, col2, col3 = st.columns(3)
    col1.metric("오늘 국내 금값", f"{kr_price:,.0f} 원/g")
    col2.metric("오늘 국제 환산가", f"{latest_intl_price:,.0f} 원/g")
    col3.metric("오늘의 괴리율 (%)", f"{disparity:.2f}%", delta=f"{disparity:.2f}%", delta_color="inverse")

    # 차트 그리기
    fig = go.Figure()

    # 국제 금값 선 그래프
    fig.add_trace(go.Scatter(
        x=df_intl.index, 
        y=df_intl['Intl_KRW_g'],
        mode='lines',
        name='국제 금 시세(원/g 환산)',
        line=dict(color='#1f77b4', width=2)
    ))

    # 우측 상단 괴리율 텍스트 박스 추가 (Annotation)
    fig.add_annotation(
        xref="paper", yref="paper",
        x=0.98, y=0.95,
        text=f"<b>오늘의 괴리율: {disparity:.2f}%</b>",
        showarrow=False,
        font=dict(size=16, color="white"),
        bgcolor="firebrick",
        bordercolor="black",
        borderwidth
