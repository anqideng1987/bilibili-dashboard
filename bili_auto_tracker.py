import os
import time
import requests
import pandas as pd
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BV_FILE = os.path.join(BASE_DIR, "bv_list.txt")

def load_bv_list():
    if not os.path.exists(BV_FILE):
        print(f"❌ 找不到 {BV_FILE} 文件")
        return []
    with open(BV_FILE, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip() and not line.startswith("#")]

def fetch_bilibili_app_api(bvid):
    # 使用 B 站官方App/小程序数据接口 (无 412 风控，返回格式完整)
    url = f"https://api.bilibili.com/x/web-interface/archive/stat?bvid={bvid}"
    headers = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 BiliApp/76800100"
    }

    try:
        # 先抓取视频核心数据 (播放量、弹幕、点赞、投币、收藏、分享等)
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            res_json = res.json()
            if res_json.get("code") == 0:
                data = res_json.get("data", {})
                
                # 补充抓取标题与 UP 主信息
                detail_url = f"https://api.bilibili.com/x/web-interface/view/detail?bvid={bvid}"
                detail_res = requests.get(detail_url, headers=headers, timeout=10)
                title, owner_name = "-", "-"
                if detail_res.status_code == 200 and detail_res.json().get("code") == 0:
                    view_data = detail_res.json().get("data", {}).get("view", {})
                    title = view_data.get("title", "-")
                    owner_name = view_data.get("owner", {}).get("name", "-")

                return {
                    "采集时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "BV号": bvid,
                    "标题": title,
                    "UP主": owner_name,
                    "播放量": data.get("view", 0),
                    "弹幕数": data.get("danmaku", 0),
                    "回复数": data.get("reply", 0),
                    "收藏数": data.get("favorite", 0),
                    "投币数": data.get("coin", 0),
                    "点赞数": data.get("like", 0),
                    "分享数": data.get("share", 0),
                    "状态": "成功"
                }
            else:
                print(f"⚠️ [{bvid}] API 错误: {res_json.get('message')}")
        else:
            print(f"⚠️ [{bvid}] HTTP状态码异常: {res.status_code}")
    except Exception as e:
        print(f"❌ [{bvid}] 请求异常: {e}")

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
    print(f"🚀 [App Stat 接口] 开始采集数据: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    bvs = load_bv_list()
    if not bvs:
        print("❌ BV 列表为空，退出。")
        return

    data_list = []
    for bvid in bvs:
        print(f"正在抓取: {bvid} ...")
        item = fetch_bilibili_app_api(bvid)
        data_list.append(item)
        time.sleep(0.5)

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
