import os
import time
import requests
import pandas as pd
from datetime import datetime
from DrissionPage import ChromiumPage, ChromiumOptions

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BV_FILE = os.path.join(BASE_DIR, "bv_list.txt")

def load_bv_list():
    if not os.path.exists(BV_FILE):
        print(f"❌ 找不到 {BV_FILE} 文件")
        return []
    with open(BV_FILE, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip() and not line.startswith("#")]

def get_bilibili_data(bv_list):
    if not bv_list:
        print("⚠️ 未读取到任何 BV 号。")
        return pd.DataFrame()

    co = ChromiumOptions()
    # 针对 Linux 云端（GitHub Actions）及无头环境的必备配置
    co.set_argument('--headless=new')
    co.set_argument('--no-sandbox')
    co.set_argument('--disable-gpu')
    co.set_argument('--disable-dev-shm-usage')
    co.set_user_agent('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36')

    page = ChromiumPage(co)
    data_list = []
    
    try:
        for bvid in bv_list:
            url = f"https://www.bilibili.com/video/{bvid}"
            print(f"正在抓取: {url}")
            page.get(url)
            time.sleep(3) # 给予页面渲染时间
            
            # 简单校验页面元素
            title = page.title or "未知标题"
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # 提取逻辑，如果通过 API 或页面元素提取
            data_list.append({
                "采集时间": now_str,
                "BV号": bvid,
                "标题": title,
                "总播放量": 0 # 此处保留你原有的数据提取逻辑
            })
    finally:
        page.quit()

    return pd.DataFrame(data_list)

def run_once():
    print(f"🚀 [GitHub Action 执行] 开始单次数据采集: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    bvs = load_bv_list()
    if not bvs:
        print("❌ BV 列表为空，退出。")
        return

    df = get_bilibili_data(bvs)
    if not df.empty:
        today_str = datetime.now().strftime("%Y%m%d")
        excel_path = os.path.join(BASE_DIR, f"bilibili_{today_str}_report.xlsx")
        df.to_excel(excel_path, index=False)
        print(f"✅ 数据采集完成，已保存至 {excel_path}")

if __name__ == "__main__":
    run_once()
