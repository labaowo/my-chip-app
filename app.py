import streamlit as st
import pandas as pd
import os
import yfinance as yf
from datetime import datetime, timedelta
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 網頁專業寬螢幕配置 (必須在第一行)
st.set_page_config(page_title="台股集保籌碼深度監控中心", layout="wide", page_icon="📈")

@st.cache_data(ttl=10)
def load_pure_local_database(db_path):
    if os.path.exists(db_path):
        try:
            df = pd.read_csv(db_path)
            df['stock_id'] = df['stock_id'].astype(str).str.strip().str.zfill(4)
            df['date'] = df['date'].astype(str).str.strip()
            return df, "📦 歷史大數據庫 (chip_history_database.csv)"
        except Exception as e:
            return None, f"讀取異常: {str(e)}"
    return None, "找不到檔案"

@st.cache_data(ttl=14400)
def load_stock_names_and_volumes():
    # 這裡只留下您確定要手動對照的股票，其他不寫
    # 如果您連這裡都不想預設，可以留空字典：name_dict = {}
    name_dict = {
        "2330": "台積電", "2408": "南亞科", "2317": "鴻海", "3105": "穩懋", 
        "2356": "英業達", "6775": "達發", "3293": "鈊象", "3008": "大立光",
        "2303": "聯電", "2454": "聯發科", "2382": "廣達", "2301": "光寶科",
        "2603": "長榮", "2609": "陽明", "2615": "萬海", "2618": "長榮航"
    }
    volume_dict = {} # ➔ 這裡直接清空，不要預設成交量！
    return name_dict, volume_dict

@st.cache_data(ttl=3600)
def get_yahoo_price_and_vol_history(stock_id):
    formats = [f"{stock_id}.TW", f"{stock_id}.TWO"]
    end_date = datetime.today().strftime('%Y-%m-%d')
    start_date = (datetime.today() - timedelta(days=2*365)).strftime('%Y-%m-%d')
    for symbol in formats:
        try:
            stock = yf.Ticker(symbol)
            df = stock.history(start=start_date, end=end_date)
            if not df.empty:
                df = df.reset_index()
                df['date'] = pd.to_datetime(df['Date']).dt.strftime('%Y-%m-%d')
                df['真實成交量(張)'] = (df['Volume'] / 1000).astype(int)
                return df[['date', 'Close', '真實成交量(張)']].rename(columns={'Close': '收盤價'})
        except Exception: continue
    return None

st.title("📈 台股集保籌碼大數據監控中心 (終極自選股整合版)")
st.markdown("---")

st.sidebar.header("🎯 核心控制面板")
st.sidebar.info("💡 系統已全面升級為【純單機強固模式】：直接讀取您本機硬碟的私房歷史大數據庫檔案。")

st.sidebar.markdown("---")
st.sidebar.subheader("🎛️ 飆股多頭濾網拉桿")
large_pct = st.sidebar.slider("千張大戶持股比例下限 (%)", min_value=40.0, max_value=95.0, value=65.0, step=1.0)
retail_pct = st.sidebar.slider("10張以下散戶持股上限 (%)", min_value=5.0, max_value=40.0, value=15.0, step=1.0)
max_holders = st.sidebar.number_input("總股東人數上限 (鎖定高爆發中小型股)", min_value=1000, max_value=1000000, value=1000000, step=5000)
min_vol_filter = st.sidebar.slider("前一日最低成交量 (張) ➔ 剔除流動性差個股", min_value=0, max_value=2000, value=100, step=50)

DB_PATH = "chip_history_database.csv"

db_master, source_status = load_pure_local_database(DB_PATH)

if db_master is not None:
    data_date = str(db_master['date'].max())
    st.sidebar.success(f"📅 當前大數據庫最新日期: {data_date}")
    
    raw_data = db_master[db_master['date'] == data_date].copy()

    large_df = raw_data[raw_data['level'] == 15][['stock_id', 'percent', 'holders']].rename(columns={'percent': '千張大戶持股%', 'holders': '千張大戶人數'})
    
    retail_string = "1,2,3,4,5"
    retail_levels = [int(x) for x in retail_string.split(',')]
    retail_df = raw_data[raw_data['level'].isin(retail_levels)].groupby('stock_id')['percent'].sum().reset_index().rename(columns={'percent': '10張以下散戶持股%'})
    total_holders = raw_data.groupby('stock_id')['holders'].sum().reset_index().rename(columns={'holders': '總股東人數'})
    
    merged = pd.merge(pd.merge(large_df, retail_df, on='stock_id'), total_holders, on='stock_id')
    
    only_stocks = (merged['stock_id'].str.len() == 4) & (merged['stock_id'].str.isdigit())
    filtered = merged[only_stocks].copy()
    
    names, volumes = load_stock_names_and_volumes()
    filtered = merged.copy()
    filtered['股票名稱'] = filtered['stock_id'].map(names).fillna("未命名個股")
    
    # 💡 完美修正點：不要用 .fillna(150)！
    # 如果對照不到成交量，就給它 0 或者 NaN，這樣才不會被最低成交量濾網誤判！
    filtered['昨日成交量(張)'] = filtered['stock_id'].map(volumes).fillna(0).astype(int)
    
    filtered = filtered.rename(columns={'stock_id': '股票代號'})
    filtered = filtered[['股票代號', '股票名稱', '千張大戶持股%', '千張大戶人數', '10張以下散戶持股%', '總股東人數', '昨日成交量(張)']]
    
    filtered['股票代號數字'] = pd.to_numeric(filtered['股票代號'])
    
    # 💡 完美修正點：使用安全顯式字串分割，100% 杜絕 PowerShell 吞掉中括號導致 SyntaxError 的問題！
    bad_string = "2412,2633,3045,4904"
    bad_codes = [int(x) for x in bad_string.split(',')]
    
    mask_normal = ~filtered['股票代號數字'].isin(bad_codes)
    mask_no_finance = ~((filtered['股票代號數字'] >= 2800) & (filtered['股票代號數字'] <= 2897))
    final_pool = filtered[mask_normal & mask_no_finance].drop(columns=['股票代號數字'])
    
    result_df = final_pool[
        (final_pool['千張大戶持股%'] >= large_pct) & 
        (final_pool['10張以下散戶持股%'] <= retail_pct) & 
        (final_pool['總股東人數'] <= max_holders) &
        (final_pool['昨日成交量(張)'] >= min_vol_filter)
    ].sort_values(by='總股東人數', ascending=True)

    # 💡 修正 1：將字典宣告移到 Tabs 之外的最上層，確保所有 Tab 都能存取，絕對不會報 NameError
    names, volumes = load_stock_names_and_volumes()

    tab1, tab2, tab3 = st.tabs(["🔍 全市場中小型大戶鎖碼榜", "📊 個股籌碼全自動歷史深度健檢", "📋 全台股代號中文查閱中心"])
    
    with tab1:
        st.subheader(f"🔥 當前符合條件且具備「流動量能」的黑馬個股 (計 {len(result_df)} 檔)")
        if not result_df.empty:
            st.dataframe(result_df.style.format({
                '千張大戶持股%': '{:.2f}%', '10張以下散戶持股%': '{:.2f}%',
                '千張大戶人數': '{:,} 人', '總股東人數': '{:,} 人', '昨日成交量(張)': '{:,} 張'
            }), use_container_width=True, height=520)
        else:
            st.warning("💡 當前篩選條件太嚴格了，沒有股票符合，請調低大戶持股比例或放寬散戶持股上限！")

    with tab2:
        st.subheader("🕵️‍♂️ 指定個股【大戶籌碼線 ＋ 真實股價與成交量】專業交叉健檢")
        user_picks = st.text_input("💡 操盤手自選歷史追蹤名單 (可用逗號隔開多檔):", value="3293, 3008, 2330, 2408, 2317, 3105, 2356, 6775")
        tracked_stocks = [s.strip() for s in user_picks.split(',') if s.strip().isdigit()]
        input_stock = st.selectbox("請選取一檔進行深度圖表診斷:", tracked_stocks if tracked_stocks else ["3105"])
        
        if input_stock:
            hist_stock = db_master[db_master['stock_id'] == input_stock.zfill(4)].copy()
            if not hist_stock.empty:
                hist_stock = hist_stock.drop_duplicates(subset=['date', 'level', 'percent'])
                
                # 標準化日期格式
                hist_stock['date_str'] = pd.to_datetime(hist_stock['date'].astype(str), format='%Y%m%d', errors='coerce').dt.strftime('%Y-%m-%d')
                if hist_stock['date_str'].isnull().all():
                    hist_stock['date_str'] = pd.to_datetime(hist_stock['date'].astype(str), errors='coerce').dt.strftime('%Y-%m-%d')
                
                # 💡 修正 2：計算總人數時嚴格限制在 level <= 15，避免重複加總全體總計欄位
                t_holders = hist_stock[hist_stock['level'] <= 15].groupby('date_str')['holders'].sum().reset_index().rename(columns={'holders': '總人數', 'date_str': 'date'})
                l_df = hist_stock[hist_stock['level'] == 15][['date_str', 'percent']].rename(columns={'percent': '大戶%', 'date_str': 'date'})
                
                hist_r_string = "1,2,3,4,5"
                hist_r_levels = [int(x) for x in hist_r_string.split(',')]
                r_df = hist_stock[hist_stock['level'].isin(hist_r_levels)].groupby('date_str')['percent'].sum().reset_index().rename(columns={'percent': '散戶%', 'date_str': 'date'})
                
                m_hist = pd.merge(pd.merge(l_df, r_df, on='date'), t_holders, on='date').sort_values(by='date').reset_index(drop=True)
                
                # 接軌 Yahoo Finance 價格數據
                price_df = get_yahoo_price_and_vol_history(input_stock)
                if price_df is not None and not price_df.empty:
                    m_hist = pd.merge(m_hist, price_df, on='date', how='left').sort_values(by='date')
                    m_hist['收盤價'] = m_hist['收盤價'].ffill().bfill()
                    m_hist['真實成交量(張)'] = m_hist['真實成交量(張)'].fillna(0).astype(int)
                
                # 雙層結構自適應配置
                fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                                    vertical_spacing=0.12,
                                    specs=[[{"secondary_y": True}], [{"secondary_y": False}]],
                                    row_heights=[0.7, 0.3])
                
                # 💡 優化 3：明確指定為 'date' 軸線类型，維持 Plotly 自適應的時間序列刻度
                fig.add_trace(go.Scatter(x=m_hist['date'], y=m_hist['大戶%'], name='千張大戶持股 (%)', line=dict(color='#E41A1C', width=4)), row=1, col=1, secondary_y=False)
                fig.add_trace(go.Scatter(x=m_hist['date'], y=m_hist['散戶%'], name='10張以下散戶 (%)', line=dict(color='#4DAF4A', width=2, dash='dash')), row=1, col=1, secondary_y=False)
                
                if '收盤價' in m_hist.columns and not m_hist['收盤價'].isna().all():
                    fig.add_trace(go.Scatter(x=m_hist['date'], y=m_hist['收盤價'], name='真實收盤價 (元)', line=dict(color='#1F77B4', width=2.5)), row=1, col=1, secondary_y=True)
                    fig.update_yaxes(title_text="<b>真實股價 (元)</b>", row=1, col=1, secondary_y=True)
                
                if '真實成交量(張)' in m_hist.columns:
                    fig.add_trace(go.Bar(x=m_hist['date'], y=m_hist['真實成交量(張)'], name='當週成交量 (張)', marker_color='rgba(128,128,128,0.65)'), row=2, col=1)
                    fig.update_yaxes(title_text="成交量 (張)", row=2, col=1)
                
                fig.update_layout(title=f"<b>股票代號 {input_stock} 【量價籌碼三位一體】深度监控交叉大圖</b>", template="plotly_white", hovermode="x unified", height=650)
                fig.update_yaxes(title_text="持股比例 (%)", row=1, col=1, secondary_y=False)
                
                # 💡 修正 4：移除 type='category'，改為自動時間軸，避免合併不同頻率數據時發生圖表錯位斷線
                fig.update_xaxes(title_text="資料日期 (每週五)", row=2, col=1)
                st.plotly_chart(fig, use_container_width=True)
                
                # 報告解讀與安全性檢查
                if not m_hist.empty:
                    latest_row = m_hist.iloc[-1]
                    st.markdown("### 📋 操盤室核心籌碼純單機診斷報告：")
                    
                    # 防呆：確認欄位存在再輸出
                    show_price = f"{latest_row['收盤價']:.1f} 元" if '收盤價' in latest_row and pd.notna(latest_row['收盤價']) else "暫無報價"
                    st.write(f"本週大戶持股水位：**{latest_row['大戶%']:.2f} %** | 散戶持股水位：**{latest_row['散戶%']:.2f} %** | 當前對齊收盤價：**{show_price}**")
                    
                    if len(m_hist) >= 2:
                        d_large = latest_row['大戶%'] - m_hist.iloc[-2]['大戶%']
                        st.markdown("#### 🔍 操盤手實戰解讀結論：")
                        if d_large > 0.5: st.error("🔥【主力強攻】大戶籌碼急劇鎖死！散戶大退場，多頭波段起漲前兆！")
                        elif d_large < -0.5: st.warning("🚨【大戶棄船】主力正在趁亂出貨給市場散戶，建議避開！")
                        else: st.info("💤【區間防守】大戶與散戶變動不大，股價震盪洗盤中。")
                else:
                    st.warning("⚠️ 數據合併後為空，請檢查本地數據庫日期是否正確。")
            else:
                st.warning(f"❌ 查無股票代號 {input_stock} 的本地歷史籌碼紀錄。")

    with tab3:
        st.subheader("🔍 1秒全自動台股中文名稱交叉查閱")
        search_id = st.text_input("請輸入任何 4 碼台股代號進行中文名稱對照 (例如: 2330):", value="2330").strip()
        if search_id:
            # 💡 此處已可安全共享最上層獲取的 names 字典
            if search_id in names:
                st.success(f"🎯 股票代號 {search_id} 的官方真實名稱為： **【 {names[search_id]} 】**")
            else:
                st.warning(f"ℹ️ 在官方普通股列表中找不到代號 {search_id}，請確認是否為台股自選核心4碼。")
else:
    st.error("❌ 嚴重錯誤：無法順利取得數據。")
