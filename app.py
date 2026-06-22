import streamlit as st
import pandas as pd
import os
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 網頁專業寬螢幕配置 (必須在第一行)
st.set_page_config(page_title="台股集保籌碼深度監控中心", layout="wide", page_icon="📈")

@st.cache_data(ttl=5)
def load_pure_local_database(db_path):
    """讀取您剛才用 PowerShell 下載的正宗集保最新 CSV (純本地強固版)"""
    if os.path.exists(db_path):
        try:
            try: df = pd.read_csv(db_path, encoding="utf-8")
            except: df = pd.read_csv(db_path, encoding="big5")
            
            # 強制對齊集保官方 Open Data 的標準 6 欄位
            df.columns = ["date", "stock_id", "level", "holders", "shares", "percent"]
            df["stock_id"] = df["stock_id"].astype(str).str.strip().str.zfill(4)
            df["date"] = df["date"].astype(str).str.strip()
            return df
        except Exception as e: st.error(f"讀取 CSV 異常: {str(e)}")
    return None

# 內建核心追蹤中文名稱
names_dict = {
    "2330": "台積電", "2408": "南亞科", "2317": "鴻海", "3105": "穩懋", 
    "2356": "英業達", "6775": "達發", "3293": "鈊象", "3008": "大立光",
    "2303": "聯電", "2454": "聯發科", "2382": "廣達", "2301": "光寶科",
    "2603": "長榮", "2609": "陽明", "2615": "萬海", "2618": "長榮航"
}

st.title("🛡️ 台灣集保結算所 — 官方正宗大數據監控中心 (100% 本地強固版)")
st.markdown("---")

st.sidebar.header("🎯 核心控制面板")
st.sidebar.info("📦 目前模式：純本地強固版\n由 PowerShell 官方直抓 CSV 提供全體數據，不連網、絕不卡死、拒絕任何假資料填充。")
st.sidebar.markdown("---")

st.sidebar.subheader("🎛️ 飆股多頭濾網拉桿")
large_pct = st.sidebar.slider("千張大戶持股比例下限 (%)", min_value=30.0, max_value=95.0, value=50.0, step=1.0)
retail_pct = st.sidebar.slider("10張以下散戶持股上限 (%)", min_value=5.0, max_value=80.0, value=25.0, step=1.0)
max_holders = st.sidebar.number_input("總股東人數上限", min_value=1000, max_value=5000000, value=1500000, step=5000)

DB_PATH = r"C:\Users\win11\Desktop\newpython\chip_analyzer\chip_history_database.csv"
db_master = load_pure_local_database(DB_PATH)

if db_master is not None:
    # 轉換日期格式以便正確排序
    db_master['date_parsed'] = pd.to_datetime(db_master['date'].astype(str), errors='coerce')
    
    # 取得最新一期日期
    latest_date_raw = db_master["date"].max()
    st.sidebar.success(f"📅 當週榜單日期: {latest_date_raw}")
    
    # 1. 計算全市場最新一期的籌碼快照
    raw_data = db_master[db_master["date"] == latest_date_raw].copy()
    
    large_df = raw_data[raw_data["level"] == 15][['stock_id', 'percent', 'holders']].rename(columns={'percent': '千張大戶持股%', 'holders': '千張大戶人數'})
    retail_df = raw_data[raw_data["level"].isin(range(1, 6))].groupby('stock_id')['percent'].sum().reset_index().rename(columns={'percent': '10張以下散戶持股%'})
    total_holders = raw_data[raw_data['level'] <= 15].groupby('stock_id')['holders'].sum().reset_index().rename(columns={'holders': '總股東人數'})
    
    merged = pd.merge(pd.merge(large_df, retail_df, on="stock_id"), total_holders, on="stock_id")
    
    # 💡 關鍵清除：只留 4 碼純數字普通股 (長度非 4 碼的 ETF 與權證在此直接抹除)
    only_stocks = (merged['stock_id'].str.len() == 4) & (merged['stock_id'].str.isdigit())
    filtered = merged[only_stocks].copy()
    
    # 掛上中文字典名稱
    filtered["股票名稱"] = filtered["stock_id"].map(names_dict)
    
    # 💡 徹底消滅「其他上市櫃」：直接刪掉沒有寫在追蹤字典裡的其他外圍股票，保持排行榜極致乾淨！
    final_pool = filtered.dropna(subset=["股票名稱"]).copy()
    
    final_pool = final_pool.rename(columns={"stock_id": "股票代號"})
    final_pool = final_pool[["股票代號", "股票名稱", "千張大戶持股%", "千張大戶人數", "10張以下散戶持股%", "總股東人數"]]
    
    result_df = final_pool[(final_pool["千張大戶持股%"] >= large_pct) & (final_pool["10張以下散戶持股%"] <= retail_pct) & (final_pool["總股東人數"] <= max_holders)].sort_values(by="千張大戶持股%", ascending=False)
    
    # 頁籤版面配置
    tab1, tab2, tab3 = st.tabs(["🔍 全市場正宗官方鎖碼榜", "📊 本地大數據歷史深度健檢", "📋 當週官方完整 1-15 級分散明細"])
    
    with tab1:
        st.subheader(f"🔥 核心追蹤股篩選結果 (當前符合計 {len(result_df)} 檔)")
        if not result_df.empty:
            st.dataframe(result_df.style.format({"千張大戶持股%": "{:.2f}%", "10張以下散戶持股%": "{:.2f}%", "千張大戶人數": "{:,} 人", "總股東人數": "{:,} 人"}), use_container_width=True, height=400)
        else:
            st.warning("💡 當前篩選條件較嚴格，請在左側放寬散戶上限或降低大戶比例拉桿！")
            
    with tab2:
        st.subheader("🕵️‍♂️ 指定個股【大戶籌碼線 ＋ 散戶線 ＋ 股東人數】本地歷史趨勢圖表")
        inspect_id = st.selectbox("請選取一檔進行本地歷史趨勢圖表診斷:", list(names_dict.keys()), index=6) # 預設選鈊象(3293)
        
        if inspect_id:
            # 直接提取本地 CSV 內所擁有的所有歷史週度資料進行統計
            hist_stock = db_master[db_master['stock_id'] == inspect_id.zfill(4)].copy()
            if not hist_stock.empty:
                # 規範日期標籤
                hist_stock['date_str'] = pd.to_datetime(hist_stock['date'].astype(str), errors='coerce').dt.strftime('%Y-%m-%d')
                if hist_stock['date_str'].isnull().all():
                    hist_stock['date_str'] = hist_stock['date']
                    
                l_df = hist_stock[hist_stock['level'] == 15][['date_str', 'percent']].rename(columns={'percent': '大戶%'})
                r_df = hist_stock[hist_stock['level'].isin(range(1, 6))].groupby('date_str')['percent'].sum().reset_index().rename(columns={'percent': '散戶%'})
                t_holders = hist_stock[hist_stock['level'] <= 15].groupby('date_str')['holders'].sum().reset_index().rename(columns={'holders': '總人數'})
                
                m_hist = pd.merge(pd.merge(l_df, r_df, on='date_str'), t_holders, on='date_str').sort_values(by='date_str').reset_index(drop=True)
                m_hist = m_hist.rename(columns={'date_str': 'date'})
                
                st.success(f"📈 本地歷史引擎已就緒！目前成功抓取到該股共 {len(m_hist)} 週的本地歷史籌碼軌跡。")
                
                # 🎨 建立完美雙軸歷史趨勢 Plotly 圖表
                fig = make_subplots(specs=[[{"secondary_y": True}]])
                fig.add_trace(go.Scatter(x=m_hist['date'], y=m_hist['大戶%'], name='千張大戶持股 (%)', line=dict(color='#E41A1C', width=4)), secondary_y=False)
                fig.add_trace(go.Scatter(x=m_hist['date'], y=m_hist['散戶%'], name='10張以下散戶 (%)', line=dict(color='#4DAF4A', width=2, dash='dash')), secondary_y=False)
                fig.add_trace(go.Scatter(x=m_hist['date'], y=m_hist['總人數'], name='總股東人數 (人)', line=dict(color='#1F77B4', width=1.5)), secondary_y=True)
                
                fig.update_layout(title=f"<b>股票代號 {inspect_id} 【本地歷史數據】主力 vs 散戶線交叉圖</b>", template="plotly_white", hovermode="x unified", height=500)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("⚠️ 數據庫中查無此股票歷史紀錄。")
                
    with tab3:
        st.subheader("📊 指定個股當週官方 1~15 級真實股權快照")
        inspect_id_tab3 = st.text_input("請輸入任何一檔台股 4 碼代號 (如 2330 或 3293):", value="3293", key="tab3_input").strip()
        if inspect_id_tab3:
            detail_df = db_master[(db_master["stock_id"] == inspect_id_tab3.zfill(4)) & (db_master["date"] == latest_date_raw)].sort_values(by="level").reset_index(drop=True)
            if not detail_df.empty:
                st.dataframe(detail_df.style.format({"holders": "{:,}", "shares": "{:,}", "percent": "{:.2f}%"}), use_container_width=True)
            else:
                st.warning("⚠️ 本地當週資料庫中查無此股票代號。")
else:
    st.error("❌ 找不到 CSV 數據庫，請確認第一步的 PowerShell 下載是否成功。")
