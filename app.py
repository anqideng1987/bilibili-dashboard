import os
import glob
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="杨博文 Bilibili 数据看板",
    page_icon="📺",
    layout="wide"
)

st.title("📈 哔哩哔哩 · 百万播放冲刺看板")

# 侧边栏：控制台
st.sidebar.header("数据控制台")
if st.sidebar.button("🔄 刷新最新数据缓存"):
    st.cache_data.clear()
    st.rerun()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

@st.cache_data(ttl=180)
def load_latest_excel():
    # 1. 匹配所有带日期的 bilibili_*_report.xlsx 或 bilibili_*.xlsx 文件
    excel_files = glob.glob(os.path.join(BASE_DIR, "bilibili_*.xlsx")) + glob.glob(os.path.join(BASE_DIR, "*.xlsx"))
    # 排除临时文件 ~$
    valid_files = [f for f in excel_files if not os.path.basename(f).startswith("~$")]
    
    if not valid_files:
        return pd.DataFrame(), None, None
        
    # 按文件修改时间取最新的一个文件
    latest_file = max(valid_files, key=os.path.getmtime)
    file_name = os.path.basename(latest_file)
    
    try:
        xls = pd.ExcelFile(latest_file)
        # 寻找优先 Sheet
        if "3. 半小时间隔明细" in xls.sheet_names:
            target_sheet = "3. 半小时间隔明细"
        elif "2. 一小时间隔明细" in xls.sheet_names:
            target_sheet = "2. 一小时间隔明细"
        elif "1. 综合分析汇总" in xls.sheet_names:
            target_sheet = "1. 综合分析汇总"
        else:
            target_sheet = xls.sheet_names[0]
            
        df = pd.read_excel(latest_file, sheet_name=target_sheet)
        return df, file_name, target_sheet
    except Exception as e:
        st.error(f"读取 Excel 文件失败: {e}")
        return pd.DataFrame(), file_name, None

df, file_name, sheet_name = load_latest_excel()

if df.empty:
    st.error("⚠️ 暂未检测到有效的 Excel 数据文件，请确认 GitHub 仓库中是否存在 `bilibili_*_report.xlsx`。")
else:
    st.sidebar.success(f"📁 数据源: {file_name}")
    if sheet_name:
        st.sidebar.info(f"📄 当前读取 Sheet: {sheet_name}")
        
    # 列名标准化与映射
    df.columns = [str(c).strip() for c in df.columns]
    col_mapping = {
        "bvid": "BV号", "BV": "BV号",
        "total_views": "总播放量", "views": "总播放量", "播放量": "总播放量", "总播放": "总播放量",
        "video_title": "标题", "视频标题": "标题", "title": "标题",
        "up": "UP主", "author": "UP主", "owner": "UP主"
    }
    df = df.rename(columns=col_mapping)

    if "BV号" in df.columns:
        # 按采集时间排序，获取每个 BV 号最新的那一条记录
        if "采集时间" in df.columns:
            df["采集时间"] = pd.to_datetime(df["采集时间"], errors='coerce')
            latest_df = df.sort_values("采集时间").groupby("BV号").last().reset_index()
        else:
            latest_df = df.groupby("BV号").last().reset_index()

        play_col = "总播放量" if "总播放量" in df.columns else None
        like_col = "点赞数" if "点赞数" in df.columns else None
        
        if play_col:
            latest_df[play_col] = pd.to_numeric(latest_df[play_col], errors='coerce').fillna(0)
            total_views = int(latest_df[play_col].sum())
        else:
            total_views = 0
            
        total_likes = int(pd.to_numeric(latest_df[like_col], errors='coerce').fillna(0).sum()) if like_col and like_col in latest_df.columns else 0
        total_videos = len(latest_df)

        col1, col2, col3 = st.columns(3)
        col1.metric("监控视频总数", f"{total_videos} 个")
        col2.metric("累计总播放量", f"{total_views:,}")
        col3.metric("累计总点赞数", f"{total_likes:,}")

        st.subheader("📊 最新视频明细数据")
        st.dataframe(latest_df, use_container_width=True)
    else:
        st.warning(f"数据表中未找到 `BV号` 列，当前可用列名为：`{list(df.columns)}`")
