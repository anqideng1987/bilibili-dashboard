import streamlit as st
import pandas as pd
import glob
import os
import re
import datetime

# 页面基础配置，看板名称：杨百万B站数据看板
st.set_page_config(
    page_title="杨百万B站数据看板",
    page_icon="🐰",
    layout="wide"
)

# 注入粉白色主题样式
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
    </style>
""", unsafe_allow_html=True)

st.markdown("""
    <div class="bili-header">
        <div class="bili-title">🐰 杨百万B站数据看板</div>
        <div class="bili-subtitle">✨ 双列紧凑网格布局 | 原生组件驱动 | 冲刺 100w 目标</div>
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
                st.error(f"❌ 未找到 `BV号` 层，当前列名为: `{list(df.columns)}`")
            else:
                df = df.dropna(subset=["BV号"])
                df["总播放量"] = pd.to_numeric(df["总播放量"], errors='coerce').fillna(0)
                
                latest_df = df.sort_values(by="总播放量", ascending=False).drop_duplicates(subset=["BV号"]).reset_index(drop=True)

                total_videos = len(latest_df)
                total_views = int(latest_df["总播放量"].sum())
                
                c1, c2 = st.columns(2)
                with c1:
                    st.metric("📌 监控视频总数", f"{total_videos} 个")
                with c2:
                    st.metric("🔥 累计总播放量", f"{total_views:,}")
                
                st.write("")

                target_views = 1_000_000  # 100w 目标

                videos_list = list(latest_df.iterrows())
                for i in range(0, len(videos_list), 2):
                    col_left, col_right = st.columns(2)
                    
                    # 左侧视频卡片
                    with col_left:
                        if i < len(videos_list):
                            idx, row = videos_list[i]
                            bvid = str(row.get("BV号", "未知BV"))
                            title = str(row.get("标题", "未知标题"))
                            views = int(row.get("总播放量", 0))
                            owner = str(row.get("UP主", "未知UP主"))
                            percent = min(views / target_views, 1.0)
                            percent_str = f"{round(percent * 100, 2)}%"
                            rank_icon = "🥇" if idx == 0 else ("🥈" if idx == 1 else ("🥉" if idx == 2 else f"#{idx+1}"))
                            
                            with st.container():
                                st.markdown(f"""
                                    <div class="bili-card">
                                        <div style="font-size: 15px; font-weight: 700; color: #333333; margin-bottom: 4px;">{rank_icon} {title}</div>
                                        <div style="font-size: 12px; color: #D46A92; margin-bottom: 8px;">
                                            <b>BV号:</b> <a href="https://www.bilibili.com/video/{bvid}" target="_blank" style="color: #D46A92;">{bvid}</a> &nbsp;|&nbsp; <b>UP主:</b> {owner}
                                        </div>
                                    </div>
                                """, unsafe_allow_html=True)
                                
                                sc1, sc2 = st.columns(2)
                                sc1.metric("当前播放", f"{views:,}")
                                sc2.metric("冲刺进度", percent_str)
                                st.progress(percent)
                                st.write("")

                    # 右侧视频卡片
                    with col_right:
                        if i + 1 < len(videos_list):
                            idx, row = videos_list[i + 1]
                            bvid = str(row.get("BV号", "未知BV"))
                            title = str(row.get("标题", "未知标题"))
                            views = int(row.get("总播放量", 0))
                            owner = str(row.get("UP主", "未知UP主"))
                            percent = min(views / target_views, 1.0)
                            percent_str = f"{round(percent * 100, 2)}%"
                            rank_icon = "🥇" if idx == 0 else ("🥈" if idx == 1 else ("🥉" if idx == 2 else f"#{idx+1}"))
                            
                            with st.container():
                                st.markdown(f"""
                                    <div class="bili-card">
                                        <div style="font-size: 15px; font-weight: 700; color: #333333; margin-bottom: 4px;">{rank_icon} {title}</div>
                                        <div style="font-size: 12px; color: #D46A92; margin-bottom: 8px;">
                                            <b>BV号:</b> <a href="https://www.bilibili.com/video/{bvid}" target="_blank" style="color: #D46A92;">{bvid}</a> &nbsp;|&nbsp; <b>UP主:</b> {owner}
                                        </div>
                                    </div>
                                """, unsafe_allow_html=True)
                                
                                sc1, sc2 = st.columns(2)
                                sc1.metric("当前播放", f"{views:,}")
                                sc2.metric("冲刺进度", percent_str)
                                st.progress(percent)
                                st.write("")

                st.markdown("---")
                st.markdown(f"<div style='text-align: center; color: #888888; font-size: 13px;'>✨ 数据源: {os.path.basename(latest_file)} &nbsp;|&nbsp; 🕒 数据最后更新时间: <b>{file_mtime}</b> ✨</div>", unsafe_allow_html=True)

    except Exception as e:
        st.error(f"❌ 读取 Excel 数据失败: {e}")
