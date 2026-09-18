import os
import time
import json
import pandas as pd
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BV_FILE = os.path.join(BASE_DIR, "bv_list.txt")

def load_bv_list():
    if not os.path.exists(BV_FILE):
        print(f"❌ 找不到 {BV_FILE} 文件")
        return []
    with open(BV_FILE, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip() and not line.startswith("#")]

def init_driver():
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36')
    
    chrome_bin = '/usr/bin/google-chrome'
    if os.path.exists(chrome_bin):
        options.binary_location = chrome_bin

    driver = webdriver.Chrome(options=options)
    return driver

def get_bilibili_data(bv_list):
    if not bv_list:
        print("⚠️ 未读取到任何 BV 号。")
        return pd.DataFrame()

    driver = init_driver()
    data_list = []

    try:
        driver.get("https://www.bilibili.com/")
        time.sleep(2)

        for bvid in bv_list:
            url = f"https://www.bilibili.com/video/{bvid}"
            print(f"正在抓取 (Selenium 模拟浏览器): {bvid} ...")

            try:
                driver.get(url)
                time.sleep(3)

                raw_data = driver.execute_script("return JSON.stringify(window.__INITIAL_STATE__);")
                if raw_data:
                    state = json.loads(raw_data)
                    video_data = state.get("videoData", {})
                    stat = video_data.get("stat", {})

                    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    title = video_data.get("title", "")
                    owner = video_data.get("owner", {}).get("name", "")
                    view = stat.get("view", 0)

                    data_list.append({
                        "采集时间": now_str,
                        "BV号": bvid,
                        "标题": title,
                        "UP主": owner,
                        "播放量": view,
                        "点赞数": stat.get("like", 0),
                        "投币数": stat.get("coin", 0),
                        "收藏数": stat.get("favorite", 0),
                        "分享数": stat.get("share", 0),
                        "评论数": stat.get("reply", 0),
                        "弹幕数": stat.get("danmaku", 0)
                    })
                    print(f"  └─ ✅ 成功: 《{title}》| 播放量: {view}")
                else:
                    print(f"  └─ ❌ 无法提取 __INITIAL_STATE__: {bvid}")

            except Exception as e:
                print(f"  └─ ❌ 抓取失败 {bvid}: {e}")

    finally:
        driver.quit()

    return pd.DataFrame(data_list)

def run_once():
    print(f"🚀 [Selenium 模拟浏览器模式] 开始采集数据: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    bvs = load_bv_list()
    if not bvs:
        print("❌ BV 列表为空，退出。")
        return

    df = get_bilibili_data(bvs)
    if not df.empty:
        today_str = datetime.now().strftime("%Y%m%d")
        excel_path = os.path.join(BASE_DIR, f"bilibili_{today_str}_report.xlsx")

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
