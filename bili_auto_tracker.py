import os
import time
import json
import pandas as pd
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

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
    # 开启 headless 无头模式
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    # 伪装真实 User-Agent
    options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36")
    
    # 规避 Selenium 特征检测
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    
    # 修改 navigator.webdriver 标记
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    # 先访问一次主页加载 Cookie
    driver.get("https://www.bilibili.com/")
    time.sleep(2)
    return driver

def fetch_data_via_browser(driver, bvid):
    # 渲染 API 接口并获取页面纯文本 JSON 内容
    target_url = f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}"
    
    try:
        driver.get(target_url)
        time.sleep(1)
        
        # 提取预设的 raw text/pre Body
        page_source = driver.find_element("tag name", "body").text
        res_json = json.loads(page_source)

        if res_json.get("code") == 0:
            data = res_json.get("data", {})
            stat = data.get("stat", {})
            owner = data.get("owner", {})

            return {
                "采集时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "BV号": bvid,
                "标题": data.get("title", ""),
                "UP主": owner.get("name", ""),
                "播放量": stat.get("view", 0),
                "弹幕数": stat.get("danmaku", 0),
                "回复数": stat.get("reply", 0),
                "收藏数": stat.get("favorite", 0),
                "投币数": stat.get("coin", 0),
                "点赞数": stat.get("like", 0),
                "分享数": stat.get("share", 0),
                "状态": "成功"
            }
        else:
            print(f"⚠️ [{bvid}] 接口返回错误: {res_json.get('message')}")
    except Exception as e:
        print(f"❌ [{bvid}] 页面解析异常: {e}")

    return {
        "采集时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "BV号": bvid,
        "标题": "获取失败",
        "UP主": "-",
        "播放量": 0,
        "弹幕数": 0,
        "回复数": 0,
        "收藏数": 0,
        "投币数": 0,
        "点赞数": 0,
        "分享数": 0,
        "状态": "失败"
    }

def run_once():
    print(f"🚀 [Chrome Driver 模拟模式] 开始采集数据: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    bvs = load_bv_list()
    if not bvs:
        print("❌ BV 列表为空，退出。")
        return

    driver = init_driver()
    data_list = []

    try:
        for bvid in bvs:
            print(f"正在抓取: {bvid} ...")
            item = fetch_data_via_browser(driver, bvid)
            data_list.append(item)
            time.sleep(1.5)
    finally:
        driver.quit()

    df = pd.DataFrame(data_list)
    if not df.empty:
        today_str = datetime.now().strftime("%Y%m%d")
        excel_path = os.path.join(BASE_DIR, f"bilibili_{today_str}_report.xlsx")
        
        if os.path.exists(excel_path):
            try:
                old_df = pd.read_excel(excel_path)
                df = pd.concat([old_df, df], ignore_index=True)
            except Exception as e:
                print(f"读取原有 Excel 异常，将重新创建: {e}")
                
        df.to_excel(excel_path, index=False)
        print(f"✅ 数据已更新保存至: {excel_path}")

if __name__ == "__main__":
    run_once()
