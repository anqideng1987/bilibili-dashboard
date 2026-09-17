import os
import glob
import pandas as pd
import datetime
import streamlit as st

# 页面基础配置
st.set_page_config(
    page_title="杨百万B站数据看板",
    page_icon="🐰",
    layout="wide"
)

# 🐰 注入粉白色主题样式与小兔子奔跑进度条动画
st.markdown("""
<style>
    /* 全局粉白色系微调 */
    .stApp {
        background-color: #FFFDFD;
    }
    h1, h2, h3 {
        color: #D46A92 !important;
    }
    .metric-card {
        background-color: #FFF0F5;
        border: 1px solid #FFD1DC;
        padding: 15px;
        border-radius: 12px;
        text-align: center;
    }
    
    /* 自定义小兔子跑动进度条容器 */
    .bunny-progress-container {
        position: relative;
        width: 100%;
        background-color: #FCE4EC;
        border-radius: 15px;
        height: 24px;
        margin: 8px 0;
        overflow: visible;
        box-shadow: inset 0 1px 3px rgba(0,0,0,0.05);
    }
    
    /* 进度条填充部分 */
    .bunny-progress-bar {
        height: 100%;
        background: linear-gradient(90deg, #FFB6C1, #FF69B4);
        border-radius: 15px;
        transition: width 0.5s ease;
    }
    
    /* 动态小兔子图标定位 */
    .bunny-runner {
        position: absolute;
        top: -24px;
        transform: translateX(-50%);
        font-size: 22px;
        animation: bunny-bounce 0.6s infinite alternate;
    }
    
    @keyframes bunny-bounce {
        from { transform: translateX(-50%) translateY(0); }
        to { transform: translateX(-50%) translateY(-3px); }
    }
</style>
""", unsafe_allow_html=True)

st.title("🐰 杨百万B站数据看板")

# 侧边栏控制台
st.sidebar.header("数据控制台")
if st.sidebar.button("🔄 刷新最新数据缓存"):
    st.cache_data.clear()
    st.rerun()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

@st.cache_data(ttl=180)
def load_dashboard_data():
    """精确读取第一个 Sheet（综合分析汇总）下方的明细表格数据"""
    search_patterns = [
        os.path.join(BASE_DIR, "bilibili_*_report.xlsx"),
        os.path.join(BASE_DIR, "bilibili_*.xlsx"),
        os.path.join(BASE_DIR, "*.xlsx")
    ]
    
    excel_files = []
    for pattern in search_patterns:
        excel_files.extend(glob.glob(pattern))
        
    valid_files = list(set([f for f in excel_files if not os.path.basename(f).startswith("~$")]))
    if not valid_files:
        return None, None, pd.DataFrame()
        
    latest_file = max(valid_files, key=os.path.getmtime)
    file_name = os.path.basename(latest_file)
    file_mtime = datetime.datetime.fromtimestamp(os.path.getmtime(latest_file)).strftime('%Y-%m-%d %H:%M:%S')
    
    try:
        # 读取第一个 Sheet，跳过前6行说明文字，第7行（index 6）作为列名
        df = pd.read_excel(latest_file, sheet_name=0, skiprows=6)
        if not df.empty:
            df.columns = df.iloc[0]
            df = df.drop(0).reset_index(drop=True)
        return file_name, file_mtime, df
    except Exception as e:
        return file_name, file_mtime, pd.DataFrame()

file_name, file_mtime, df = load_dashboard_data()

if df.empty or "BV号" not in df.columns:
    st.warning("⚠️ **未能在第一个 Sheet 中检测到有效的视频数据**，请确认 Excel 结构是否包含 `BV号`、`UP主`、`标题`、`总播放` 等列。")
else:
    # 数据清洗与格式化
    df = df.dropna(subset=["BV号"]).copy()
    df["总播放"] = pd.to_numeric(df["总播放"], errors='coerce').fillna(0)
    
    # 按播放量从高到低排序，并对重复的 BV 号取播放量最高或最新的一条
    df = df.sort_values(by="总播放", ascending=False).drop_duplicates(subset=["BV号"]).reset_index(drop=True)

    target_views = 1000000  # 100w 目标
    total_videos = len(df)
    cumulative_views = int(df["总播放"].sum())

    # 顶栏核心指标看板
    col1, col2, col3 = st.columns(3)
    col1.metric("监控视频总数", f"{total_videos} 个")
    col2.metric("累计总播放量", f"{cumulative_views:,}")
    col3.metric("冲刺百万目标进度", f"{(cumulative_views / (total_videos * target_views) * 100):.2f}%" if total_videos > 0 else "0%")

    st.markdown("---")
    st.subheader("📊 视频播放量排行及百万冲刺进度")

    # 循环渲染每个视频的粉白色精美卡片及小兔子进度条
    for index, row in df.iterrows():
        bvid = str(row.get("BV号", ""))
        title = str(row.get("标题", "未知标题"))
        up = str(row.get("UP主", "未知UP主"))
        views = int(row.get("总播放", 0))
        
        # 计算单个视频距离100w的百分比 (最高限制100%)
        pct = min(float(views / target_views) * 100, 100.0)
        
        # 渲染卡片
        with st.container():
            st.markdown(f"""
            <div style="background-color: #FFF0F5; border: 1px solid #FFD1DC; padding: 16px; border-radius: 12px; margin-bottom: 14px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                    <div>
                        <span style="background-color: #FF69B4; color: white; padding: 2px 8px; border-radius: 6px; font-weight: bold; font-size: 13px;"># {index + 1}</span>
                        <b style="font-size: 16px; color: #333333; margin-left: 8px;">{title}</b>
                    </div>
                    <div style="text-align: right;">
                        <span style="color: #888888; font-size: 13px;">UP主: <b>{up}</b> | BV号: <a href="https://www.bilibili.com/video/{bvid}" target="_blank" style="color: #FF69B4; text-decoration: none;">{bvid}</a></span>
                    </div>
                </div>
                <div style="display: flex; justify-content: space-between; font-size: 14px; color: #555555; margin-bottom: 4px;">
                    <span>当前播放量: <b style="color: #D46A92; font-size: 16px;">{views:,}</b> / 1,000,000</span>
                    <span><b>{pct:.1f}%</b></span>
                </div>
                <!-- 小兔子奔跑进度条 -->
                <div class="bunny-progress-container">
                    <div class="bunny-progress-bar" style="width: {pct}%;"></div>
                    <div class="bunny-runner" style="left: {max(pct, 3.0)}%;">🐰</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

# 最下面显示数据更新时间
st.markdown("---")
st.markdown(f"<div style='text-align: center; color: #888888; font-size: 13px;'>✨ 数据源文件: {file_name} &nbsp;|&nbsp; 🕒 最后的更新时间: <b>{file_mtime}</b> ✨</div>", unsafe_allow_html=True)
