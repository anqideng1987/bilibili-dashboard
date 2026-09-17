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
def load_excel_metadata():
    """只负责寻找最新文件并解析所有 Sheet 的名称和数据，绝对不包含任何 UI 控件"""
    excel_files = glob.glob(os.path.join(BASE_DIR, "bilibili_*_report.xlsx"))
    if not excel_files:
        excel_files = glob.glob(os.path.join(BASE_DIR, "bilibili_*.xlsx"))
        
    valid_files = [f for f in excel_files if not os.path.basename(f).startswith("~$")]
    
    if not valid_files:
        return None, None, {}
        
    latest_file = max(valid_files, key=os.path.getmtime)
    file_name = os.path.basename(latest_file)
    
    try:
        xls = pd.ExcelFile(latest_file)
        sheets_data = {}
        for s_name in xls.sheet_names:
            sheets_data[s_name] = pd.read_excel(latest_file, sheet_name=s_name)
        return file_name, xls.sheet_names, sheets_data
    except Exception as e:
        return file_name, [], {}

# 获取数据
file_name, available_sheets, sheets_data = load_excel_metadata()

if not file_name or not available_sheets:
    st.error("⚠️ 暂未检测到有效的 Excel 数据文件，请确认 GitHub 仓库中是否存在 `bilibili_*_report.xlsx`。")
else:
    st.sidebar.success(f"📁 数据源: {file_name}")
    
    # 【UI 控件放在缓存函数外面】侧边栏多时间维度对比切换
    st.sidebar.markdown("---")
    st.sidebar.subheader("📋 数据表单选择")
    
    default_idx = 0
    for idx, s_name in enumerate(available_sheets):
        if "半小时" in s_name or "3." in s_name:
            default_idx = idx
            break
        elif "一小时" in s_name or "2." in s_name:
            default_idx = idx
            
    sheet_name = st.sidebar.selectbox("切换查看的对比维度", available_sheets, index=default_idx)
    st.sidebar.info(f"📄 当前读取: {sheet_name}")
    
    # 提取当前选中的 DataFrame
    df = sheets_data.get(sheet_name, pd.DataFrame())

    if df.empty:
        st.warning(f"当前 Sheet `{sheet_name}` 内容为空。")
    else:
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

            st.subheader(f"📊 最新视频明细数据 ({sheet_name})")
            st.dataframe(latest_df, use_container_width=True)
        else:
            st.warning(f"数据表中未找到 `BV号` 列，当前可用列名为：`{list(df.columns)}`")
