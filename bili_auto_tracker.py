import os
import time
import requests
import pandas as pd
from datetime import datetime, timezone, timedelta

# 定义新加坡时区 (UTC+8)
SGT = timezone(timedelta(hours=8))

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BV_FILE = os.path.join(BASE_DIR, "bv_list.txt")

SESSDATA = os.environ.get("SESSDATA", "")

def load_bv_list():
    if not os.path.exists(BV_FILE):
        print(f"❌ 找不到 {BV_FILE} 文件")
        return []
    with open(BV_FILE, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip() and not line.startswith("#")]

def fetch_bilibili_api(bvid, sessdata=""):
    url = "https://api.bilibili.com/x/web-interface/view"
    params = {"bvid": bvid}
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Referer": f"https://www.bilibili.com/video/{bvid}",
        "Origin": "https://www.bilibili.com",
        "Accept": "application/json, text/plain, */*",
        "Cookie": f"SESSDATA={sessdata.strip()};" if sessdata else ""
    }

    # 获取当前新加坡时间
    current_time_sgt = datetime.now(SGT).strftime("%Y-%m-%d %H:%M:%S")

    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        if response.status_code == 200:
            res_json = response.json()
            if res_json.get("code") == 0:
                data = res_json.get("data", {})
                stat = data.get("stat", {})
                owner = data.get("owner", {})
                
                title = data.get("title", "")
                view_count = stat.get("view", 0)
                print(f"  └─ ✅ 成功: 《{title}》| 播放量: {view_count}")
                
                return {
                    "采集时间": current_time_sgt,
                    "BV号": bvid,
                    "标题": title,
                    "UP主": owner.get("name", ""),
                    "播放量": view_count,
                    "弹幕数": stat.get("danmaku", 0),
                    "回复数": stat.get("reply", 0),
                    "收藏数": stat.get("favorite", 0),
                    "投币数": stat.get("coin", 0),
                    "点赞数": stat.get("like", 0),
                    "分享数": stat.get("share", 0),
                    "状态": "成功"
                }
            else:
                print(f"⚠️ [{bvid}] API错误: {res_json.get('message')}")
        else:
            print(f"⚠️ [{bvid}] HTTP状态码异常: {response.status_code}")
    except Exception as e:
        print(f"❌ [{bvid}] 请求异常: {e}")

    return {
        "采集时间": current_time_sgt,
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
    now_sgt = datetime.now(SGT)
    print(f"🚀 [API 模式] 开始采集数据 (新加坡时间): {now_sgt.strftime('%Y-%m-%d %H:%M:%S')}")
    
    bvs = load_bv_list()
    if not bvs:
        print("❌ BV 列表为空，退出。")
        return

    data_list = []
    for bvid in bvs:
        print(f"正在抓取: {bvid} ...")
        item = fetch_bilibili_api(bvid, SESSDATA)
        data_list.append(item)
        time.sleep(1)

    df = pd.DataFrame(data_list)
    if not df.empty:
        # 使用新加坡时间的日期作为文件名后缀 (格式: YYYYMMDD)
        date_str = now_sgt.strftime("%Y%m%d")
        excel_path = os.path.join(BASE_DIR, f"bilibili_{date_str}_report.xlsx")
        
        if os.path.exists(excel_path):
            try:
                old_df = pd.read_excel(excel_path)
                df = pd.concat([old_df, df], ignore_index=True)
            except Exception as e:
                print(f"读取原有 Excel 异常，将重新创建: {e}")
                
        df.to_excel(excel_path, index=False)
        print(f"✅ 数据采集完成，已保存至 {excel_path}")

if __name__ == "__main__":
    run_once()
