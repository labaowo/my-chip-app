import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 網頁配置 (寬螢幕、高階黑化質感)
st.set_page_config(page_title="台股3年官方集保籌碼監控中心", layout="wide", page_icon="📊")

@st.cache_data(ttl=28800)  # 快取8小時，避免頻繁重複呼叫 API 被阻擋
def fetch_3year_chip_history(stock_id):
    """聯網動態抓取過去 3 年的官方集保戶股權歷史資料"""
    # 計算 3 年前的日期
    start_date = (datetime.today() - timedelta(days=3*365)).strftime('%Y-%m-%d')
    
    # 呼叫 FinMind 官方開放資料集
    url = f"https://finmindtrade.com{stock_id}&start_date={start_date}"
    
    try:
        res = requests.get(url, timeout=15)
        data = res.json()
        if data['status'] == 200 and len(data['data']) > 0:
            df = pd.DataFrame(data['data'])
            # 確保型態與命名正確
            df['HoldingSharesLevel'] = df['HoldingSharesLevel'].astype(int)
            df['percent'] = df['percent'].astype(float)
            df['people'] = df['people'].astype(int)
            return df
    except Exception as e:
        st.error(f"❌ 數據庫聯線異常: {str(e)}")
    return pd.DataFrame()

# UI 介面設計
st.title("📊 台灣官方集保戶股權分散表 — 3年深度歷史監控中心")
st.markdown("---")

# 側邊欄控制
st.sidebar.header("🎯 核心控制面板")
stock_input = st.sidebar.text_input("💡 請輸入欲健檢的台股代號 (4碼):", value="3293").strip()

if stock_input:
    # 開始動態撈取 3 年資料
    st.info(f"🚀 正在即時抓取 {stock_input} 過去 3 年的每週五官方集保數據...")
    raw_chip = fetch_3year_chip_history(stock_input)
    
    if not raw_chip.empty:
        # --- 數據清洗與統計 ---
        # 1. 提取千張大戶 (Level 15)
        large_chip = raw_chip[raw_chip['HoldingSharesLevel'] == 15][['date', 'percent', 'people']].rename(
            columns={'percent': '千張大戶持股%', 'people': '千張大戶人數'}
        )
        
        # 2. 提取 10張以下散戶 (Level 1~5)
        retail_chip = raw_chip[raw_chip['HoldingSharesLevel'].isin([1, 2, 3, 4, 5])].groupby('date')['percent'].sum().reset_index().rename(
            columns={'percent': '10張以下散戶持股%'}
        )
        
        # 3. 計算全體總股東人數 (Level 1~15)
        total_holders = raw_chip[raw_chip['HoldingSharesLevel'] <= 15].groupby('date')['people'].sum().reset_index().rename(
            columns={'people': '總股東人數'}
        )
        
        # 合併所有籌碼軌跡
        m_chip = pd.merge(pd.merge(large_chip, retail_chip, on='date'), total_holders, on='date').sort_values(by='date').reset_index(drop=True)
        
        # 顯示最新一週的官方表格快照 (Level 1-16)
        latest_date = m_chip['date'].max()
        st.success(f"📅 官方最新公告集保日期：{latest_date}")
        
        # 呈現最新一週完整的 1-15 級分散表
        st.subheader(f"📋 {stock_input} 最新一週官方持股分級明細表 ({latest_date})")
        snapshot_df = raw_chip[raw_chip['date'] == latest_date].sort_values(by='HoldingSharesLevel').reset_index(drop=True)
        snapshot_df = snapshot_df.rename(columns={
            'HoldingSharesLevel': '持股分級(Level)', 'people': '股東人數(人)', 'unit': '持股總股數(股)', 'percent': '持股比例(%)'
        })[['持股分級(Level)', '股東人數(人)', '持股總股數(股)', '持股比例(%)']]
        
        st.dataframe(snapshot_df.style.format({
            '股東人數(人)': '{:,}', '持股總股數(股)': '{:,}', '持股比例(%)': '{:.2f}%'
        }), use_container_width=True, height=250)
        
        # --- 繪製 3 年大戶/散戶持股比例對照圖 ---
        st.markdown("---")
        st.subheader(f"📈 {stock_input} 過去 3 年【每週五大戶 vs 散戶】籌碼歷史趨勢大圖")
        
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        # 紅線：大戶
        fig.add_trace(go.Scatter(x=m_chip['date'], y=m_chip['千張大戶持股%'], name='千張大戶持股 (%)', line=dict(color='#E41A1C', width=3.5)), secondary_y=False)
        # 綠虛線：散戶
        fig.add_trace(go.Scatter(x=m_chip['date'], y=m_chip['10張以下散戶持股%'], name='10張以下散戶 (%)', line=dict(color='#4DAF4A', width=2, dash='dash')), secondary_y=False)
        # 藍細線：總股東人數 (放右軸)
        fig.add_trace(go.Scatter(x=m_chip['date'], y=m_chip['總股東人數'], name='總股東人數 (人)', line=dict(color='#984EA3', width=1.5)), secondary_y=True)
        
        fig.update_layout(template="plotly_white", hovermode="x unified", height=500, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        fig.update_yaxes(title_text="持股比例 (%)", secondary_y=False)
        fig.update_yaxes(title_text="總股東人數 (人)", secondary_y=True)
        fig.update_xaxes(title_text="每週五公告日期")
        st.plotly_chart(fig, use_container_width=True)
        
        # --- 數據導出功能 (讓您可以下載這 3 年完整的累加乾淨數據) ---
        st.markdown("---")
        st.subheader("💾 籌碼歷史大數據導出")
        csv_data = m_chip.to_csv(index=False).encode('utf-8')
        st.download_button(
            label=f"📥 下載 {stock_input} 過去3年每週五清洗後的籌碼大數據 CSV 檔案",
            data=csv_data,
            file_name=f"{stock_input}_3year_chip_history.csv",
            mime="text/csv"
        )
    else:
        st.warning("⚠️ 無法取得該股歷史集保數據，請確認該股票在 3 年內是否有上市櫃交易。")
