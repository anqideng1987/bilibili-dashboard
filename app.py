import streamlit as st
import pandas as pd
import glob
import os

st.set_page_config(
    page_title="哔哩哔哩 · 百万播放冲刺看板",
    page_icon="📺",
    layout="wide"
)

st.markdown("""
    <style>
    .stApp { background-color: #FFF5F7; }
    .bili-header {
        background: linear-gradient(135deg, #FA7298 0%, #FF8EB3 100%);
        padding: 24px;
        border-radius: 16px;
        color: white;
        box-shadow: 0 4px 15px rgba(250, 114, 152, 0.25);
        margin-bottom: 25px;
        text-align: center;
    }
    .bili-title { font-size: 32px; font-weight: 800; margin: 0; }
    .bili-subtitle { font-size: 14px; opacity: 0.9; margin-top: 6px; }
    .bili-card {
        background-color: #FFFFFF;
        border: 2px solid #FFE4ED;
        border-radius: 16px;
        padding: 20px 24px;
        margin-bottom: 20px;
        box-shadow: 0 6px 12px rgba(250, 114, 152, 0.08);
    }
    .video-title { font-size: 18px; font-weight: 700; color: #212121; margin-bottom: 8px; }
    .bv-badge {
        background-color: #FFEAEF; color: #FA7298;
        padding: 3px 10px; border-radius: 12px;
        font-size: 12px; font-weight: 600; display: inline-block; margin-bottom: 12px;
    }
    .stat-box { background: #FFF0F4; border-radius: 12px; padding: 12px 16px; text-align: center; }
    .stat-label { font-size: 13px; color: #757575; margin-bottom: 4px; }
    .stat-value { font-size: 22px; font-weight: 800; color: #FA7298; }
    .stProgress > div > div > div > div {
        background-image: linear-gradient(90deg, #FF92B4 0%, #FA7298 100%);
        border-radius: 10px;
    }
    .stProgress > div > div { background-color: #FFEAEF; border-radius: 10px; height: 14px; }
    </style>
""", unsafe_allow_html=True)

st.markdown("""
    <div class="bili-header">
        <div class="bili-title">📺 哔哩哔哩 · 目标百万播放冲刺看板</div>
        <div class="bili-subtitle">✨ 实时追踪视频播放进度 | 自动适配各种表格格式</div>
    </div>
""", unsafe_allow_html=True)

all_excel_files = glob.glob("*.xlsx") + glob.glob("*.xls")
valid_excel_files = [f for f in all_excel_files if not os.path.basename(f).startswith("~$")]

if not valid_excel_files:
    st.warning("🌸 暂未找到任何 .xlsx 数据文件，请将表格文件提交至仓库根目录。")
else:
    latest_file = max(valid_excel_files, key=os.path.getmtime)
    mtime_str = pd.to_datetime(os.path.getmtime(latest_file), unit='s').strftime('%Y-%m-%d %H:%M:%S')
    st.info(f"📊 当前自动加载最新数据源：`{latest_file}`（更新时间: {mtime_str}）")
    
    try:
        xls = pd.ExcelFile(latest_file)
        
        # 优先选择含完整明细数据的 Sheet
        if "3. 半小时间隔明细" in xls.sheet_names:
            df = pd.read_excel(latest_file, sheet_name="3. 半小时间隔明细")
        elif "2. 一小时间隔明细" in xls.sheet_names:
            df = pd.read_excel(latest_file, sheet_name="2. 一小时间隔明细")
        elif "1. 综合分析汇总" in xls.sheet_names:
            # “1. 综合分析汇总” 前 7 行是指标解读，跳过前 7 行读取
            df = pd.read_excel(latest_file, sheet_name="1. 综合分析汇总", skiprows=7)
        else:
            df = pd.read_excel(latest_file, sheet_name=xls.sheet_names[0])
            
        if not df.empty:
            # 清理表头空格
            df.columns = [str(c).strip() for c in df.columns]
            
            # 智能映射常见列名
            col_mapping = {
                "bvid": "BV号", "BV": "BV号", "bv号": "BV号",
                "total_views": "总播放量", "views": "总播放量", "播放量": "总播放量", "总播放": "总播放量",
                "video_title": "标题", "视频标题": "标题", "title": "标题",
                "up": "UP主", "author": "UP主", "owner": "UP主"
            }
            df = df.rename(columns=col_mapping)

            if "BV号" not in df.columns:
                st.error(f"❌ 读取成功但未找到 `BV号` 列，当前表格的列名为: `{list(df.columns)}`")
            else:
                # 过滤掉可能存在的空行
                df = df.dropna(subset=["BV号"])
                
                # 按时间获取每个 BV 号的最新记录
                if "采集时间" in df.columns:
                    df["采集时间"] = pd.to_datetime(df["采集时间"], errors='coerce')
                    latest_df = df.sort_values("采集时间").groupby("BV号").last().reset_index()
                else:
                    latest_df = df.groupby("BV号").last().reset_index()

                total_videos = len(latest_df)
                
                # 提取播放量
                if "总播放量" in latest_df.columns:
                    latest_df["总播放量"] = pd.to_numeric(latest_df["总播放量"], errors='coerce').fillna(0)
                    total_views = int(latest_df["总播放量"].sum())
                else:
                    total_views = 0
                
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown(f'<div class="stat-box"><div class="stat-label">📌 当前监控视频数量</div><div class="stat-value">{total_videos} 个</div></div>', unsafe_allow_html=True)
                with c2:
                    st.markdown(f'<div class="stat-box"><div class="stat-label">🔥 监控视频累计总播放量</div><div class="stat-value">{total_views:,}</div></div>', unsafe_allow_html=True)
                
                st.write("")
                st.write("")

                for _, row in latest_df.iterrows():
                    bvid = str(row.get("BV号", "未知BV"))
                    title = str(row.get("标题", "未知标题"))
                    views = int(row.get("总播放量", 0))
                    owner = str(row.get("UP主", "未知UP主"))
                    target = 1_000_000
                    
                    progress = min(views / target, 1.0)
                    gap = max(target - views, 0)
                    percent = round(progress * 100, 2)
                    
                    st.markdown(f"""
                        <div class="bili-card">
                            <div class="video-title">🎬 {title}</div>
                            <div>
                                <span class="bv-badge">{bvid}</span>
                                <span style="font-size:13px; color:#757575; margin-left:8px;">UP主：{owner}</span>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    col1, col2, col3 = st.columns([2, 2, 3])
                    with col1:
                        st.markdown(f'<div class="stat-box"><div class="stat-label">当前总播放</div><div class="stat-value">{views:,}</div></div>', unsafe_allow_html=True)
                    with col2:
                        gap_text = f"{gap:,}" if gap > 0 else "🎉 已破百万！"
                        st.markdown(f'<div class="stat-box"><div class="stat-label">距离 100 万还差</div><div class="stat-value" style="color: {"#FA7298" if gap > 0 else "#4CAF50"};">{gap_text}</div></div>', unsafe_allow_html=True)
                    with col3:
                        st.markdown(f"**🌸 冲刺进度：<span style='color:#FA7298; font-size:18px;'>{percent}%</span>**", unsafe_allow_html=True)
                        st.progress(progress)
                    
                    st.write("")
    except Exception as e:
        st.error(f"❌ 读取 Excel 数据失败: {e}")
