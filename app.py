import os
import glob
import pandas as pd
import streamlit as st

st.set_page_config(page_title="杨博文 Bilibili 数据看板", layout="wide")

st.title("📈 Bilibili 视频数据监控看板")

# 侧边栏：刷新与数据源检查
st.sidebar.header("数据控制台")
if st.sidebar.button("🔄 刷新最新数据缓存"):
    st.cache_data.clear()
    st.rerun()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

@st.cache_data(ttl=300)
def load_data():
    # 优先读取历史数据库 history_db.csv，没有则自动找最新的 bilibili_*.xlsx
    csv_path = os.path.join(BASE_DIR, "history_db.csv")
    if os.path.exists(csv_path):
        df = pd.read_csv(csv_path, encoding='utf-8-sig')
        return df, "history_db.csv"
    
    excel_files = glob.glob(os.path.join(BASE_DIR, "bilibili_*_report.xlsx"))
    if excel_files:
        latest_file = max(excel_files, key=os.path.getmtime)
        df = pd.read_excel(latest_file)
        return df, os.path.basename(latest_file)
        
    return pd.DataFrame(), None

df, source_file = load_data()

if df.empty:
    st.error("⚠️ 暂未检测到数据文件，请确认 GitHub 仓库中是否存在 `history_db.csv` 或 `bilibili_*_report.xlsx`。")
else:
    st.sidebar.success(f"当前数据源: {source_file}")
    
    # 兼容字段名称
    play_col = "总播放量" if "总播放量" in df.columns else ("播放量" if "播放量" in df.columns else None)
    like_col = "点赞数" if "点赞数" in df.columns else None
    
    if play_col:
        # 获取每个 BV 号最新的记录
        if "BV号" in df.columns:
            latest_df = df.groupby("BV号").last().reset_index()
        else:
            latest_df = df
            
        total_views = latest_df[play_col].sum()
        total_likes = latest_df[like_col].sum() if like_col else 0
        total_videos = len(latest_df)
        
        # 顶部数据大卡片
        col1, col2, col3 = st.columns(3)
        col1.metric("监控视频总数", f"{total_videos} 个")
        col2.metric("累计总播放量", f"{total_views:,}")
        col3.metric("累计总点赞数", f"{total_likes:,}")
        
        st.subheader("📊 详细数据明细")
        st.dataframe(latest_df, use_container_width=True)
    else:
        st.warning("数据表中找不到播放量相关字段，请检查文件列名。")
