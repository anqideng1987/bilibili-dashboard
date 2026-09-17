import os
import time
import pandas as pd
from datetime import datetime, timezone, timedelta
from DrissionPage import ChromiumPage, ChromiumOptions

# 设置新加坡时区 (UTC+8)
SGT = timezone(timedelta(hours=8))

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BV_FILE = os.path.join(BASE_DIR, "bv_list.txt")

def load_bv_list():
    if not os.path.exists(BV_FILE):
        print(f"❌ 找不到 {BV_FILE} 文件")
        return []
    with open(BV_FILE, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip() and not line.startswith("#")]

def init_drission_page():
    """初始化适配 Xvfb 虚拟环境的 ChromiumPage"""
    co = ChromiumOptions()

    # 1. 在 Xvfb 中以“有头/真实屏幕”模式运行，避免使用 headless 被反爬识别
    # co.set_argument('--headless=new')  <-- Xvfb 环境下显式注释掉

    # 2. Linux 容器环境必备参数
    co.set_argument('--no-sandbox')                  # 禁用沙盒权限限制
    co.set_argument('--disable-dev-shm-usage')       # 禁用 /dev/shm 内存限制，防止内存溢出崩溃
    co.set_argument('--disable-gpu')                 # 禁用 GPU 硬件加速
    co.set_argument('--window-size=1920,1080')       # 设置标准屏幕分辨率

    # 3. 反爬虫与浏览器特征伪装
    co.set_argument('--disable-blink-features=AutomationControlled')
    co.set_user_agent('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36')

    # 4. 指定系统中 Chrome 浏览器的可执行路径
    chrome_paths = ['/usr/bin/google-chrome', '/usr/bin/chromium-browser', '/usr/bin/chromium']
    for path in chrome_paths:
        if os.path.exists(path):
            co.set_browser_path(path)
            break

    return ChromiumPage(co)

def fetch_bilibili_data_dp(page, bvid):
    url = f"https://www.bilibili.com/video/{bvid}"
    current_time_sgt = datetime.now(SGT).strftime("%Y-%m-%d %H:%M:%S")

    try:
        page.get(url)
        # 等待关键变量渲染完成
        page.wait.load_start()
        time.sleep(1.5)

        # 从页面全局变量中提取结构化数据
        state = page.run_js('return window.__INITIAL_STATE__ || {};')
        if state and 'videoData' in state:
            video_data = state.get('videoData', {})
            stat = video_data.get('stat', {})
            owner = video_data.get('owner', {})

            title = video_data.get('title', '')
            view_count = stat.get('view', 0)
            print(f"  └─ ✅ 成功: 《{title}》| 播放量: {view_count}")

            return {
                "采集时间": current_time_sgt,
                "BV号": bvid,
                "标题": title,
                "UP主": owner.get('name', ''),
                "播放量": view_count,
                "弹幕数": stat.get('danmaku', 0),
                "回复数": stat.get('reply', 0),
                "收藏数": stat.get('favorite', 0),
                "投币数": stat.get('coin', 0),
                "点赞数": stat.get('like', 0),
                "分享数": stat.get('share', 0),
                "状态": "成功"
            }
        else:
            print(f"⚠️ [{bvid}] 未能在 window.__INITIAL_STATE__ 中查找到数据")
    except Exception as e:
        print(f"❌ [{bvid}] 请求异常: {e}")

    return {
        "采集时间": current_time_sgt,
        "BV号": bvid,
        "标题": "获取失败",
        "UP主": "-",
        "播放量": 0, "弹幕数": 0, "回复数": 0, "收藏数": 0, "投币数": 0, "点赞数": 0, "分享数": 0,
        "状态": "失败"
    }

def run_once():
    now_sgt = datetime.now(SGT)
    print(f"🚀 [DrissionPage + Xvfb 模式] 开始采集数据: {now_sgt.strftime('%Y-%m-%d %H:%M:%S')}")

    bvs = load_bv_list()
    if not bvs:
        print("❌ BV 列表为空，退出。")
        return

    page = init_drission_page()
    data_list = []

    try:
        for bvid in bvs:
            print(f"正在抓取: {bvid} ...")
            item = fetch_bilibili_data_dp(page, bvid)
            data_list.append(item)
            time.sleep(1)
    finally:
        page.quit()

    df = pd.DataFrame(data_list)
    if not df.empty:
        date_str = now_sgt.strftime("%Y%m%d")
        excel_path = os.path.join(BASE_DIR, f"bilibili_{date_str}_report.xlsx")

        if os.path.exists(excel_path):
            try:
                old_df = pd.read_excel(excel_path)
                df = pd.concat([old_df, df], ignore_index=True)
            except Exception as e:
                print(f"读取原有 Excel 异常: {e}")

        df.to_excel(excel_path, index=False)
        print(f"✅ 数据采集完成，已保存至 {excel_path}")

if __name__ == "__main__":
    run_once()
