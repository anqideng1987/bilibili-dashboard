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

# 注入粉白色主题、卡片样式以及小兔子跑动进度条动画
st.markdown("""
    <style>
    .stApp { background-color: #FFFDFD; }
    .bili-header {
        background: linear-gradient(135deg, #FFB6C1 0%, #FF69B4 100%);
        padding: 24px;
        border-radius: 16px;
        color: white;
        box-shadow: 0 4px 15px rgba(255, 105, 180, 0.25);
        margin-bottom: 25px;
        text-align: center;
    }
    .bili-title { font-size: 32px; font-weight: 800; margin: 0; }
    .bili-subtitle { font-size: 14px; opacity: 0.95; margin-top: 6px; }
    .bili-card {
        background-color: #FFF0F5;
        border: 1px solid #FFD1DC;
        border-radius: 16px;
        padding: 20px 24px;
        margin-bottom: 20px;
        box-shadow: 0 6px 12px rgba(255, 182, 193, 0.15);
    }
    .video-title { font-size: 18px; font-weight: 700; color: #333333; margin-bottom: 8px; }
    .bv-badge {
        background-color: #FFEAEF; color: #D46A92;
        padding: 3px 10px; border-radius: 12px;
        font-size: 12px; font-weight: 600; display: inline-block; margin-bottom: 12px;
    }
    .stat-box { background: #FFFFFF; border-radius: 12px; padding: 12px 16px; text-align: center; border: 1px solid #FFE4ED; }
    .stat-label { font-size: 13px; color: #757575; margin-bottom: 4px; }
    .stat-value { font-size: 22px; font-weight: 800; color: #D46A92; }

    /* 自定义小兔子跑动进度条容器 */
    .bunny-progress-container {
        position: relative;
        width: 100%;
        background-color: #FCE4EC;
        border-radius: 15px;
        height: 22px;
        margin: 12px 0 4px 0;
        overflow: visible;
        box-shadow: inset 0 1px 3px rgba(0,0,0,0.05);
    }
    .bunny-progress-bar {
        height: 100%;
        background: linear-gradient(90deg, #FFB6C1, #FF69B4);
        border-radius: 15px;
        transition: width 0.5s ease;
    }
    .bunny-runner {
        position: absolute;
        top: -22px;
        transform: translateX(-50%);
        font-size: 20px;
        animation: bunny-bounce 0.6s infinite alternate;
    }
    @keyframes bunny-bounce {
        from { transform: translateX(-50%) translateY(0); }
        to { transform: translateX(-50%) translateY(-3px); }
    }
    </style>
""", unsafe_allow_html=True)

st.markdown("""
    <div class="bili-header">
        <div class="bili-title">🐰 杨百万B站数据看板</div>
        <div class="bili-subtitle">✨ 综合分析汇总数据源 | 视频列表按播放量降序排列 | 冲刺100万目标</div>
    </div>
""", unsafe_allow_html=True)

# 获取所有 xlsx / xls 文件（排除隐藏与缓存文件）
all_excel_files = glob.glob("*.xlsx") + glob.glob("*.xls")
valid_excel_files = [f for f in all_excel_files if not os.path.basename(f).startswith("~$")]

if not valid_excel_files:
    st.warning("🌸 暂未找到任何 .xlsx 数据文件，请将表格文件提交至仓库根目录。")
else:
    date_files = [f for f in valid_excel_files if re.search(r'\d{8}', f)]
    latest_file = sorted(date_files, key=lambda x: re.search(r'\d{8}', x).group())[-1] if date_files else sorted(valid_excel_files)[-1]
    
    # 获取文件修改时间作为数据更新时间
    file_mtime = datetime.datetime.fromtimestamp(os.path.getmtime(latest_file)).strftime('%Y-%m-%d %H:%M:%S')
    
    st.info(f"📊 当前自动加载最新数据源：`{latest_file}`")
    
    try:
        # 直接读取第一个 Sheet（综合分析汇总），该表第 7 行（index 6）是真正的明细表头
        df = pd.read_excel(latest_file, sheet_name=0, skiprows=6)
        if not df.empty:
            df.columns = df.iloc[0]
            df = df.drop(0).reset_index(drop=True)
            
            # 标准化列名映射
            col_mapping = {
                "BV号": "BV号", "bv号": "BV号",
                "总播放": "总播放量", "总播放量": "总播放量", "播放量": "总播放量",
                "标题": "标题", "视频标题": "标题",
                "UP主": "UP主", "up主": "UP主"
            }
            df = df.rename(columns=col_mapping)

            if "BV号" not in df.columns:
                st.error(f"❌ 读取第一个 Sheet 成功但未找到 `BV号` 列，当前列名为: `{list(df.columns)}`")
            else:
                df = df.dropna(subset=["BV号"])
                
                # 转换总播放量为数值格式
                df["总播放量"] = pd.to_numeric(df["总播放量"], errors='coerce').fillna(0)
                
                # 按播放量从高到低（降序）排序，并去除重复的BV号
                latest_df = df.sort_values(by="总播放量", ascending=False).drop_duplicates(subset=["BV号"]).reset_index(drop=True)

                total_videos = len(latest_df)
                total_views = int(latest_df["总播放量"].sum())
                
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown(f'<div class="stat-box"><div class="stat-label">📌 当前监控视频数量</div><div class="stat-value">{total_videos} 个</div></div>', unsafe_allow_html=True)
                with c2:
                    st.markdown(f'<div class="stat-box"><div class="stat-label">🔥 监控视频累计总播放量</div><div class="stat-value">{total_views:,}</div></div>', unsafe_allow_html=True)
                
                st.write("")
                st.write("")

                target_views = 1_000_000  # 100w 目标

                # 遍历显示按播放量排序后的视频列表
                for idx, row in latest_df.iterrows():
                    bvid = str(row.get("BV号", "未知BV"))
                    title = str(row.get("标题", "未知标题"))
                    views = int(row.get("总播放量", 0))
                    owner = str(row.get("UP主", "未知UP主"))
                    
                    progress = min(views / target_views, 1.0)
                    gap = max(target_views - views, 0)
                    percent = min(round((views / target_views) * 100, 2), 100.0)
                    
                    rank_icon = "🥇" if idx == 0 else ("🥈" if idx == 1 else ("🥉" if idx == 2 else f"#{idx+1}"))
                    
                    st.markdown(f"""
                        <div class="bili-card">
                            <div class="video-title">{rank_icon} {title}</div>
                            <div>
                                <span class="bv-badge"><a href="https://www.bilibili.com/video/{bvid}" target="_blank" style="color: #D46A92; text-decoration: none;">{bvid}</a></span>
                                <span style="font-size:13px; color:#757575; margin-left:8px;">UP主：{owner}</span>
                            </div>
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 10px;">
                                <span style="font-size: 14px; color: #555555;">当前播放: <b style="color: #D46A92; font-size: 16px;">{views:,}</b> / 1,000,000</span>
                                <span style="font-size: 14px; color: #D46A92; font-weight: bold;">进度: {percent}%</span>
                            </div>
                            <!-- 小兔子奔跑进度条 -->
                            <div class="bunny-progress-container">
                                <div class="bunny-progress-bar" style="width: {percent}%;"></div>
                                <div class="bunny-runner" style="left: {max(percent, 3.0)}%;">🐰</div>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
                    
                # 最下面显示数据更新的时间
                st.markdown("---")
                st.markdown(f"<div style='text-align: center; color: #888888; font-size: 13px;'>✨ 数据源文件: {os.path.basename(latest_file)} &nbsp;|&nbsp; 🕒 数据的最后更新时间: <b>{file_mtime}</b> ✨</div>", unsafe_allow_html=True)

    except Exception as e:
        st.error(f"❌ 读取 Excel 数据失败: {e}")
