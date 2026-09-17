import streamlit as st
import pandas as pd
import glob
import os
import re
import datetime

# 页面基础配置
st.set_page_config(
    page_title="杨百万B站数据看板",
    page_icon="🐰",
    layout="wide"
)

# 注入粉白色主题、每 10w 刻度节点、粉色渐变进度条和小兔子跟随动画的精美样式
st.markdown("""
    <style>
    .stApp { background-color: #FFFDFD; }
    .bili-header {
        background: linear-gradient(135deg, #FFB6C1 0%, #FF69B4 100%);
        padding: 20px;
        border-radius: 16px;
        color: white;
        box-shadow: 0 4px 15px rgba(255, 105, 180, 0.25);
        margin-bottom: 20px;
        text-align: center;
    }
    .bili-title { font-size: 28px; font-weight: 800; margin: 0; }
    .bili-subtitle { font-size: 13px; opacity: 0.95; margin-top: 6px; }
    
    .bili-card {
        background-color: #FFF0F5;
        border: 1px solid #FFD1DC;
        border-radius: 14px;
        padding: 16px;
        margin-bottom: 16px;
        box-shadow: 0 4px 10px rgba(255, 182, 193, 0.12);
    }
    .video-title { 
        font-size: 15px; 
        font-weight: 700; 
        color: #333333; 
        margin-bottom: 6px; 
        white-space: nowrap; 
        overflow: hidden; 
        text-overflow: ellipsis; 
    }
    .bv-badge {
        background-color: #FFEAEF; color: #D46A92;
        padding: 2px 8px; border-radius: 10px;
        font-size: 11px; font-weight: 600; display: inline-block; margin-bottom: 8px;
    }
    .stat-box { background: #FFFFFF; border-radius: 10px; padding: 6px 10px; text-align: center; border: 1px solid #FFE4ED; }
    .stat-label { font-size: 11px; color: #757575; margin-bottom: 2px; }
    .stat-value { font-size: 16px; font-weight: 800; color: #D46A92; }

    /* 每 10w 播放量一个节点的里程碑粉色渐变进度条容器 */
    .milestone-container {
        position: relative;
        width: 100%;
        background-color: #FCE4EC;
        border-radius: 12px;
        height: 16px;
        margin: 16px 0 4px 0;
    }
    .milestone-bar {
        height: 100%;
        background: linear-gradient(90deg, #FFB6C1, #FF69B4);
        border-radius: 12px;
        transition: width 0.5s ease;
    }
    .bunny-runner {
        position: absolute;
        top: -22px;
        transform: translateX(-50%);
        font-size: 18px;
        animation: bunny-bounce 0.6s infinite alternate;
    }
    @keyframes bunny-bounce {
        from { transform: translateX(-50%) translateY(0); }
        to { transform: translateX(-50%) translateY(-3px); }
    }
    .milestone-ticks {
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        display: flex;
        justify-content: space-between;
        pointer-events: none;
        padding: 0 2px;
    }
    .tick {
        width: 1px;
        height: 100%;
        background-color: rgba(255, 255, 255, 0.8);
    }
    .milestone-labels {
        display: flex;
        justify-content: space-between;
        font-size: 9px;
        color: #888888;
        padding: 0 2px;
        margin-top: 2px;
    }
    </style>
""", unsafe_allow_html=True)

# 渲染精美视频卡片（包含粉色渐变进度条、小兔子跟随、10w 刻度节点）
def render_video_card(idx, row, target_views):
    bvid = str(row.get("BV号", "未知BV"))
    title = str(row.get("标题", "未知标题"))
    views = int(row.get("总播放量", 0))
    owner = str(row.get("UP主", "未知UP主"))
    
    percent_val = min(round((views / target_views) * 100, 2), 100.0)
    rank_icon = "🥇" if idx == 0 else ("🥈" if idx == 1 else ("🥉" if idx == 2 else f"#{idx+1}"))
    
    card_html = f"""
        <div class="bili-card">
            <div class="video-title" title="{title}">{rank_icon} {title}</div>
            <div>
                <span class="bv-badge"><a href="https://www.bilibili.com/video/{bvid}" target="_blank" style="color: #D46A92; text-decoration: none;">{bvid}</a></span>
                <span style="font-size:12px; color:#757575; margin-left:6px;">UP主：{owner}</span>
            </div>
            
            <div style="display: flex; gap: 8px; margin-top: 6px;">
                <div style="flex: 1;" class="stat-box">
                    <div class="stat-label">当前播放</div>
                    <div class="stat-value">{views:,}</div>
                </div>
                <div style="flex: 1;" class="stat-box">
                    <div class="stat-label">冲刺进度</div>
                    <div class="stat-value">{percent_val}%</div>
                </div>
            </div>
            
            <!-- 每 10w 播放量一个节点的粉色渐变进度条与小兔子跟随 -->
            <div class="milestone-container">
                <div class="milestone-bar" style="width: {percent_val}%;"></div>
                <div class="milestone-ticks">
                    <div class="tick"></div><div class="tick"></div><div class="tick"></div><div class="tick"></div><div class="tick"></div>
                    <div class="tick"></div><div class="tick"></div><div class="tick"></div><div class="tick"></div><div class="tick"></div><div class="tick"></div>
                </div>
                <div class="bunny-runner" style="left: {max(percent_val, 3.0)}%;">🐰</div>
            </div>
            <div class="milestone-labels">
                <span>0w</span><span>20w</span><span>40w</span><span>60w</span><span>80w</span><span>100w</span>
            </div>
        </div>
    """
    st.markdown(card_html, unsafe_allow_html=True)


st.markdown("""
    <div class="bili-header">
        <div class="bili-title">🐰 杨百万B站数据看板</div>
        <div class="bili-subtitle">✨ 双列紧凑网格布局 | 每 10w 播放量一个里程碑节点 | 冲刺 100w 目标</div>
    </div>
""", unsafe_allow_html=True)

# 获取所有 xlsx / xls 文件
all_excel_files = glob.glob("*.xlsx") + glob.glob("*.xls")
valid_excel_files = [f for f in all_excel_files if not os.path.basename(f).startswith("~$")]

if not valid_excel_files:
    st.warning("🌸 暂未找到任何 .xlsx 数据文件，请将表格文件提交至仓库根目录。")
else:
    date_files = [f for f in valid_excel_files if re.search(r'\d{8}', f)]
    latest_file = sorted(date_files, key=lambda x: re.search(r'\d{8}', x).group())[-1] if date_files else sorted(valid_excel_files)[-1]
    
    file_mtime = datetime.datetime.fromtimestamp(os.path.getmtime(latest_file)).strftime('%Y-%m-%d %H:%M:%S')
    
    try:
        df = pd.read_excel(latest_file, sheet_name=0, skiprows=6)
        if not df.empty:
            df.columns = df.iloc[0]
            df = df.drop(0).reset_index(drop=True)
            
            col_mapping = {
                "BV号": "BV号", "bv号": "BV号",
                "总播放": "总播放量", "总播放量": "总播放量", "播放量": "总播放量",
                "标题": "标题", "视频标题": "标题",
                "UP主": "UP主", "up主": "UP主"
            }
            df = df.rename(columns=col_mapping)

            if "BV号" not in df.columns:
                st.error(f"❌ 未找到 `BV号` 列，当前列名为: `{list(df.columns)}`")
            else:
                df = df.dropna(subset=["BV号"])
                df["总播放量"] = pd.to_numeric(df["总播放量"], errors='coerce').fillna(0)
                
                latest_df = df.sort_values(by="总播放量", ascending=False).drop_duplicates(subset=["BV号"]).reset_index(drop=True)

                total_videos = len(latest_df)
                total_views = int(latest_df["总播放量"].sum())
                
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown(f'<div class="stat-box"><div class="stat-label">📌 监控视频总数</div><div class="stat-value" style="font-size:18px;">{total_videos} 个</div></div>', unsafe_allow_html=True)
                with c2:
                    st.markdown(f'<div class="stat-box"><div class="stat-label">🔥 累计总播放量</div><div class="stat-value" style="font-size:18px;">{total_views:,}</div></div>', unsafe_allow_html=True)
                
                st.write("")

                target_views = 1_000_000  # 100w 目标

                videos_list = list(latest_df.iterrows())
                for i in range(0, len(videos_list), 2):
                    col_left, col_right = st.columns(2)
                    
                    with col_left:
                        if i < len(videos_list):
                            idx, row = videos_list[i]
                            render_video_card(idx, row, target_views)
                            
                    with col_right:
                        if i + 1 < len(videos_list):
                            idx, row = videos_list[i + 1]
                            render_video_card(idx, row, target_views)

                st.markdown("---")
                st.markdown(f"<div style='text-align: center; color: #888888; font-size: 13px;'>✨ 数据源: {os.path.basename(latest_file)} &nbsp;|&nbsp; 🕒 数据最后更新时间: <b>{file_mtime}</b> ✨</div>", unsafe_allow_html=True)

    except Exception as e:
        st.error(f"❌ 读取 Excel 数据失败: {e}")
