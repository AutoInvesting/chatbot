import streamlit as st
import yfinance as yf
import pandas as pd
import requests
from bs4 import BeautifulSoup
import plotly.graph_objects as go

# 1. 페이지 설정
st.set_page_config(page_title="금 시세 괴리율 분석", layout="wide")

# 2. 국내 금 시세 가져오기 (네이버)
def get_korea_gold():
    try:
        url = "https://finance.naver.com/marketindex/goldDetail.naver"
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        soup = BeautifulSoup(res.text, 'html.parser')
        price_text = soup.select_one('.value').text
        return float(price_text.replace(',', ''))
    except:
        return None

# 3. 국제 데이터 가져오기 (야후 파이낸스)
@st.cache_data(ttl=3600)
def load_data():
    try:
        gold = yf.download('GC=F', period='1y')['Close']
        fx = yf.download('KRW=X', period='1y')['Close']
        df = pd.concat([gold, fx], axis=1)
        df.columns = ['USD_oz', 'FX']
        df = df.dropna()
        # 원/g 환산 (1oz = 31.1034768g)
        df['Intl_KRW_g'] = (df['USD_oz'] * df['FX']) / 31.1034768
        return df
    except:
        return pd.DataFrame()

# 메인 화면
st.title("💰 금 시세 국내/국제 괴리율 분석")

kr_price = get_korea_gold()
df_intl = load_data()

if kr_price and not df_intl.empty:
    latest_intl = df_intl['Intl_KRW_g'].iloc[-1]
    disparity = ((kr_price - latest_intl) / latest_intl) * 100

    # 상단 지표
    c1, c2, c3 = st.columns(3)
    c1.metric("국내 금값 (원/g)", f"{kr_price:,.0f}")
    c2.metric("국제 환산가 (원/g)", f"{latest_intl:,.0f}")
    c3.metric("오늘의 괴리율", f"{disparity:.2f}%")

    # 차트 (가장 단순하고 안전한 형태)
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df_intl.index, 
        y=df_intl['Intl_KRW_g'],
        name='국제 금 시세(원/g)'
    ))
    
    fig.update_layout(
        title="최근 1년 국제 금 시세 추이",
        template="plotly_white",
        hovermode="x unified"
    )
    
    st.plotly_chart(fig, use_container_width=True)
    st.info(f"현재 국내가와 국제 환산가의 차이(괴리율)는 {disparity:.2f}% 입니다.")

else:
    st.warning("데이터 로딩 중입니다. 잠시 후 새로고침 해주세요.")
