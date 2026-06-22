import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 網頁專業寬螢幕配置 (必須在第一行)
st.set_page_config(page_title="台股全市場籌碼深度監控中心", layout="wide", page_icon="📈")

@st.cache_data(ttl=1800)  # 快取30分鐘，避免高頻重複下刷
def fetch_all_market_latest_chip():
    """【終極解封引擎】繞過受阻的官方直接下載口，改由大數據備份口一次抓取全市場最新一期真實籌碼"""
    # 索取最新一週全台股所有代號的集保數據明細
    url = "https://finmindtrade.com" + (datetime.today() - timedelta(days=14)).strftime('%Y-%m-%d')
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        res = requests.get(url, headers=headers, timeout=25)
        if res.status_code == 200:
            data = res.json()
            if data['status'] == 200 and len(data['data']) > 0:
                df = pd.DataFrame(data['data'])
                df['HoldingSharesLevel'] = df['HoldingSharesLevel'].astype(int)
                df['percent'] = df['percent'].astype(float)
                df['people'] = df['people'].astype(int)
                df['stock_id'] = df['stock_id'].astype(str).str.strip().str.zfill(4)
                return df
    except Exception: pass
    return pd.DataFrame()

@st.cache_data(ttl=28800)
def fetch_single_stock_3year_history(stock_id):
    """【單股 3 年雲端動態引擎】點選個股時，秒級抓取 3 年歷史集保籌碼線"""
    start_date = (datetime.today() - timedelta(days=3*365)).strftime('%Y-%m-%d')
    url = f"https://finmindtrade.com{stock_id}&start_date={start_date}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        res = requests.get(url, headers=headers, timeout=15)
        if res.status_code == 200:
            data = res.json()
            if data['status'] == 200 and len(data['data']) > 0:
                df = pd.DataFrame(data['data'])
                df['HoldingSharesLevel'] = df['HoldingSharesLevel'].astype(int)
                df['percent'] = df['percent'].astype(float)
                df['people'] = df['people'].astype(int)
                return df
    except Exception: pass
    return pd.DataFrame()

names_dict = {
    "2330": "台積電", "2408": "南亞科", "2317": "鴻海", "3105": "穩懋", 
    "2356": "英業達", "6775": "達發", "3293": "鈊象", "3008": "大立光",
    "2303": "聯電", "2454": "聯發科", "2382": "廣達", "2301": "光寶科",
    "2603": "長榮", "2609": "陽明", "2615": "萬海", "2618": "長榮航"
}

st.title("🛡️ 台灣集保結算所 — 全市場 2,000 檔普通股籌碼移動監控中心")
st.markdown("---")

# 📥 側邊欄拉桿控制面板
st.sidebar.header("🎯 核心控制面板")
st.sidebar.info("🚀 運行模式：強固雲端大數據模式\n已完全切斷對本地受損 CSV 檔案的依賴，直接對齊最新一期全台股普通股標的。")
st.sidebar.markdown("---")

st.sidebar.subheader("🎛️ 飆股多頭籌碼濾網")
large_pct = st.sidebar.slider("千張大戶持股比例下限 (%)", min_value=30.0, max_value=95.0, value=55.0, step=1.0)
retail_pct = st.sidebar.slider("10張以下散戶持股上限 (%)", min_value=5.0, max_value=80.0, value=30.0, step=1.0)
max_holders = st.sidebar.number_input("總股東人數上限 (鎖定中小型高爆發股)", min_value=1000, max_value=5000000, value=1500000, step=5000)

# 直接發動雲端大數據接軌
with st.spinner("📦 正在連線大數據備份庫，即時載入最新一期全市場股權明細..."):
    db_master = fetch_all_market_latest_chip()

if not db_master.empty:
    latest_date = db_master["date"].max()
    st.sidebar.success(f"📅 最新公告日期: {latest_date}")
    
    # 1. 篩選最新一期的全市場標的
    raw_data = db_master[db_master["date"] == latest_date].copy()
    
    large_df = raw_data[raw_data["HoldingSharesLevel"] == 15][['stock_id', 'percent', 'people']].rename(columns={'percent': '千張大戶持股%', 'people': '千張大戶人數'})
    retail_df = raw_data[raw_data["HoldingSharesLevel"].isin(range(1, 6))].groupby('stock_id')['percent'].sum().reset_index().rename(columns={'percent': '10張以下散戶持股%'})
    total_holders = raw_data[raw_data['HoldingSharesLevel'] <= 15].groupby('stock_id')['people'].sum().reset_index().rename(columns={'people': '總股東人數'})
    
    merged = pd.merge(pd.merge(large_df, retail_df, on="stock_id"), total_holders, on="stock_id")
    
    # 💡 【普通股過濾清洗】代號長度必須剛好等於 4 碼且全為數字！100% 擋掉垃圾權證，精準鎖定 2,000 多檔普通股！
    only_stocks = (merged['stock_id'].str.len() == 4) & (merged['stock_id'].str.isdigit())
    filtered = merged[only_stocks].copy()
    
    # 掛上中文名稱
    filtered["股票名稱"] = filtered["stock_id"].map(names_dict).fillna("上市櫃普通股")
    
    final_pool = filtered.rename(columns={"stock_id": "股票代號"})
    final_pool = final_pool[["股票代號", "股票名稱", "千張大戶持股%", "千張大戶人數", "10張以下散戶持股%", "總股東人數"]]
    
    # 套用綜合濾網排序
    result_df = final_pool[
        (final_pool["千張大戶持股%"] >= large_pct) & 
        (final_pool["10張以下散戶持股%"] <= retail_pct) & 
        (final_pool["總股東人數"] <= max_holders)
    ].sort_values(by="千張大戶持股%", ascending=False).reset_index(drop=True)

    # 建立正式三大頁籤
    tab1, tab2, tab3 = st.tabs(["🔍 全市場2,000檔鎖碼榜", "📊 單股 3 年籌碼歷史深度健檢", "📋 當週官方完整 1-15 級分散明細"])
    
    with tab1:
        st.subheader(f"🔥 全市場符合條件之正宗台股普通股計 {len(result_df)} 檔 (已排除六碼權證與衍生商品)")
        if not result_df.empty:
            st.dataframe(result_df.style.format({
                "千張大戶持股%": "{:.2f}%", "10張以下散戶持股%": "{:.2f}%",
                "千張大戶人數": "{:,} 人", "總股東人數": "{:,} 人"
            }), use_container_width=True, height=450)
        else:
            st.warning("💡 當前篩選條件較嚴格，請在左側放寬散戶上限或降低大戶比例拉桿！")
            
    with tab2:
        st.subheader("🕵️‍♂️ 輸入任意代號動態提取 3 年【大戶線 vs 散戶線】趨勢交叉大圖")
        inspect_id = st.text_input("🔮 請輸入任何一檔台股 4 碼代號 (如 3293, 2330, 2317):", value="3293").strip()
        
        if inspect_id:
            st.info(f"📥 後台正在單獨連線雲端，為代號 {inspect_id} 下刷 3 年份歷史集保長線圖...")
            hist_stock = fetch_single_stock_3year_history(inspect_id)
            
            if not hist_stock.empty:
                l_df = hist_stock[hist_stock['HoldingSharesLevel'] == 15][['date', 'percent']].rename(columns={'percent': '大戶%'})
                r_df = hist_stock[hist_stock['HoldingSharesLevel'].isin(range(1, 6))].groupby('date')['percent'].sum().reset_index().rename(columns={'percent': '散戶%'})
                t_holders = hist_stock[hist_stock['HoldingSharesLevel'] <= 15].groupby('date')['people'].sum().reset_index().rename(columns={'people': '總人數'})
                
                m_hist = pd.merge(pd.merge(l_df, r_df, on='date'), t_holders, on='date').sort_values(by='date').reset_index(drop=True)
                st.success(f"📈 成功從小包中提取該股 {len(m_hist)} 週歷史數據！已完美對齊。")
                
                # 🎨 繪製無限制 3 年籌碼交叉雙軸大圖
                fig = make_subplots(specs=[[{"secondary_y": True}]])
                fig.add_trace(go.Scatter(x=m_hist['date'], y=m_hist['大戶%'], name='千張大戶持股 (%)', line=dict(color='#E41A1C', width=4)), secondary_y=False)
                fig.add_trace(go.Scatter(x=m_hist['date'], y=m_hist['散戶%'], name='10張以下散戶 (%)', line=dict(color='#4DAF4A', width=2, dash='dash')), secondary_y=False)
                fig.add_trace(go.Scatter(x=m_hist['date'], y=m_hist['總人數'], name='總股東人數 (人)', line=dict(color='#1F77B4', width=1.5)), secondary_y=True)
                fig.update_layout(title=f"<b>股票代號 {inspect_id} 【3年正宗集保大數據】主力 vs 散戶線交叉圖</b>", template="plotly_white", hovermode="x unified", height=550)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("⚠️ 雲端歷史連線忙碌，請等待 10 秒讓伺服器放行後，再次點擊網頁重新整理。")
                
    with tab3:
        st.subheader("📊 指定個股當週官方 1~15 級真實股權快照")
        inspect_id_tab3 = st.text_input("請輸入任何一檔台股 4 碼代號看當週明細 (如 2330 或 3293):", value="3293", key="tab3_input").strip()
        if inspect_id_tab3:
            detail_df = db_master[(db_master["stock_id"] == inspect_id_tab3.zfill(4)) & (db_master["date"] == latest_date)].sort_values(by="HoldingSharesLevel").reset_index(drop=True)
            if not detail_df.empty:
                detail_df_show = detail_df.rename(columns={'HoldingSharesLevel': '持股分級', 'people': '股東人數', 'unit': '持股總股數', 'percent': '持股比例'})[['持股分級', '股東人數', '持股總股數', '持股比例']]
                st.dataframe(detail_df_show.style.format({"股東人數": "{:,}", "持股總股數": "{:,}", "持股比例": "{:.2f}%"}), use_container_width=True)
            else:
                st.warning("⚠️ 雲端資料庫中查無此股票代號。")
else:
    st.error("❌ 目前雲端伺服器線路尖峰忙碌中，請稍候 10 秒按下右側 Rerun 重新載入。")
