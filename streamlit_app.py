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
    df_intl = load_intl
