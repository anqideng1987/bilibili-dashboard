import os
import time
import pandas as pd
from datetime import datetime
from DrissionPage import ChromiumPage, ChromiumOptions

# 获取当前脚本所在路径
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BV_FILE = os.path.join(BASE_DIR, "bv_list.txt")

# 支持通过 GitHub Secrets / 环境变量传入 SESSDATA
SESSDATA = os.environ.get("SESSDATA", "")

def load_bv_list():
    """读取 bv_list.txt 中的 BV 号"""
    if not os.path.exists(BV_FILE):
        print(f"❌ 找不到 {BV_FILE} 文件，请确保文件存放在仓库根目录。")
        return []
    with open(BV_FILE, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip() and not line.startswith("#")]

def create_headless_browser():
    """创建适用于 GitHub Actions 云端 Linux 环境的无头 Chrome 浏览器"""
    co = ChromiumOptions()
    
    # 云端无头模式必备参数
    co.headless()  # 开启无头模式
    co.set_argument('--no-sandbox')  # 禁用沙盒（Actions root 权限必须）
    co.set_argument('--disable-dev-shm-usage')  # 解决内存不足崩溃问题
    co.set_argument('--disable-gpu')
    co.set_argument('--window-size=1920,1080')
    co.set_user_agent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36')
    
    return ChromiumPage(co)

def fetch_bilibili_data_dp(page, bvid):
    """使用 DrissionPage 访问视频页面并解析数据"""
    url = f"https://www.bilibili.com/video/{bvid}"
    print(f"🌐 正在通过 DrissionPage 访问页面: {url}")
    
    try:
        page.get(url)
        # 等待页面核心节点加载完成
        time.sleep(3)
        
        # 提取 window.__INITIAL_STATE__ 数据结构
        init_state = page.run_js("return window.__INITIAL_STATE__;")
        
        if init_state and "videoData" in init_state:
            vdata = init_state.get("videoData", {})
            stat = vdata.get("stat", {})
            owner = vdata.get("owner", {})
            
            return {
                "采集时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "BV号": bvid,
                "标题": vdata.get("title", ""),
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
            print(f"⚠️ [{bvid}] 未能解析到 window.__INITIAL_STATE__，尝试备用 DOM 提取...")
            title = page.title or ""
            return {
                "采集时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "BV号": bvid,
                "标题": title.replace("_哔哩哔哩_bilibili", "").strip(),
                "UP主": "-",
                "播放量": 0,
                "弹幕数": 0,
                "回复数": 0,
                "收藏数": 0,
                "投币数": 0,
                "点赞数": 0,
                "分享数": 0,
                "状态": "DOM解析"
            }
            
    except Exception as e:
        print(f"❌ [{bvid}] DrissionPage 抓取异常: {e}")

    return {
        "采集时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "BV号": bvid,
        "标题": "抓取失败",
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
    """主程序：单次运行并追加写入 Excel"""
    print(f"🚀 [DrissionPage 云端模式] 开始运行采集: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    bvs = load_bv_list()
    if not bvs:
        print("❌ BV 列表为空，程序退出。")
        return

    page = create_headless_browser()
    
    # 如果设置了 SESSDATA，先注入 B 站 Cookie 保持登录态
    if SESSDATA:
        print("🔑 正在注入 SESSDATA Cookie...")
        page.get("https://www.bilibili.com")
        page.set.cookie({"name": "SESSDATA", "value": SESSDATA.strip(), "domain": ".bilibili.com"})

    data_list = []
    try:
        for bvid in bvs:
            item = fetch_bilibili_data_dp(page, bvid)
            data_list.append(item)
            time.sleep(1.5)
    finally:
        page.quit()  # 确保释放 Chrome 进程

    df_new = pd.DataFrame(data_list)
    if not df_new.empty:
        today_str = datetime.now().strftime("%Y%m%d")
        excel_path = os.path.join(BASE_DIR, f"bilibili_{today_str}_report.xlsx")
        
        # 存在同名 Excel 则自动追加，不存在则新建
        if os.path.exists(excel_path):
            try:
                old_df = pd.read_excel(excel_path)
                df_final = pd.concat([old_df, df_new], ignore_index=True)
            except Exception as e:
                print(f"读取旧 Excel 异常，重置文件: {e}")
                df_final = df_new
        else:
            df_final = df_new

        df_final.to_excel(excel_path, index=False)
        print(f"✅ 数据已成功写入 Excel: {excel_path}")

if __name__ == "__main__":
    run_once()
