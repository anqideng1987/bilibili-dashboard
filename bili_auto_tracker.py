import os
import time
import pandas as pd
from datetime import datetime, timezone, timedelta
from DrissionPage import ChromiumPage, ChromiumOptions

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
    co = ChromiumOptions()
    co.set_argument('--headless=new')
    co.set_argument('--no-sandbox')
    co.set_argument('--disable-dev-shm-usage')
    co.set_argument('--disable-gpu')
    co.set_argument('--disable-software-rasterizer')
    co.set_argument('--window-size=1920,1080')
    co.set_argument('--disable-blink-features=AutomationControlled')
    co.set_user_agent('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36')

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
        time.sleep(2)

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

def save_to_excel(df_new, excel_path):
    if os.path.exists(excel_path):
        try:
            raw_df = pd.read_excel(excel_path, header=None)
            header_idx = None
            for idx, row in raw_df.iterrows():
                row_str = " ".join([str(x) for x in row.values])
                if "BV号" in row_str and "采集时间" in row_str:
                    header_idx = idx
                    break

            if header_idx is not None:
                meta_rows = raw_df.iloc[:header_idx]
                data_df = pd.read_excel(excel_path, skiprows=header_idx)
                updated_data_df = pd.concat([data_df, df_new], ignore_index=True)
                
                with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
                    meta_rows.to_excel(writer, index=False, header=False, sheet_name='Sheet1')
                    updated_data_df.to_excel(writer, index=False, startrow=header_idx, sheet_name='Sheet1')
                print(f"✅ 成功兼容原有表头格式并追加数据至 {excel_path}")
                return
        except Exception as e:
            print(f"⚠️ 兼容追加写入失败，降级为覆盖保存: {e}")

    df_new.to_excel(excel_path, index=False)
    print(f"✅ 数据采集完成，已保存至 {excel_path}")

def run_once():
    now_sgt = datetime.now(SGT)
    print(f"🚀 [DrissionPage 模式] 开始采集数据: {now_sgt.strftime('%Y-%m-%d %H:%M:%S')}")

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

    df_new = pd.DataFrame(data_list)
    if not df_new.empty:
        date_str = now_sgt.strftime("%Y%m%d")
        excel_path = os.path.join(BASE_DIR, f"bilibili_{date_str}_report.xlsx")
        save_to_excel(df_new, excel_path)

if __name__ == "__main__":
    run_once()
