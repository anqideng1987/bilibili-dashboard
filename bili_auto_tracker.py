import os
import time
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
    co.set_argument('--headless=new')
    co.set_argument('--no-sandbox')
    co.set_argument('--disable-gpu')
    co.set_argument('--disable-dev-shm-usage')
    co.set_user_agent('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36')

    chrome_paths = ['/usr/bin/google-chrome', '/usr/bin/chromium-browser', '/usr/bin/chromium']
    for cp in chrome_paths:
        if os.path.exists(cp):
            co.set_browser_path(cp)
            break

    page = ChromiumPage(co)
    data_list = []
    
    try:
        page.get("https://www.bilibili.com/")
        time.sleep(2)

        for bvid in bv_list:
            url = f"https://www.bilibili.com/video/{bvid}"
            print(f"正在抓取: {bvid} ...")
            
            try:
                page.get(url)
                time.sleep(2.5)
                
                res = page.run_js("""
                    let data = window.__INITIAL_STATE__ || {};
                    let videoData = data.videoData || {};
                    let stat = videoData.stat || {};
                    return {
                        title: videoData.title || document.title || "",
                        owner: (videoData.owner && videoData.owner.name) || "",
                        view: stat.view || 0,
                        like: stat.like || 0,
                        coin: stat.coin || 0,
                        favorite: stat.favorite || 0,
                        share: stat.share || 0,
                        reply: stat.reply || 0,
                        danmaku: stat.danmaku || 0
                    };
                """)
                
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                data_list.append({
                    "采集时间": now_str,
                    "BV号": bvid,
                    "标题": res.get("title", ""),
                    "UP主": res.get("owner", ""),
                    "播放量": res.get("view", 0),
                    "点赞数": res.get("like", 0),
                    "投币数": res.get("coin", 0),
                    "收藏数": res.get("favorite", 0),
                    "分享数": res.get("share", 0),
                    "评论数": res.get("reply", 0),
                    "弹幕数": res.get("danmaku", 0)
                })
                print(f"  └─ ✅ 成功: 《{res.get('title')}》| 播放量: {res.get('view')}")
            except Exception as e:
                print(f"  └─ ❌ 抓取失败 {bvid}: {e}")
    finally:
        page.quit()

    return pd.DataFrame(data_list)

def run_once():
    print(f"🚀 [DrissionPage 模式] 开始采集数据: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
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
