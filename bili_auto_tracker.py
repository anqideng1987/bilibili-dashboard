import os
import time
import requests
import pandas as pd
from datetime import datetime, timezone, timedelta

# 设定新加坡/北京时间 (UTC+8)
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
        "Cookie": f"SESSDATA={sessdata.strip()};" if sessdata else ""
    }
    
    now_str = datetime.now(SGT).strftime("%Y-%m-%d %H:%M:%S")

    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        if response.status_code == 200:
            res_json = response.json()
            if res_json.get("code") == 0:
                data = res_json.get("data", {})
                stat = data.get("stat", {})
                owner = data.get("owner", {})
                
                pubdate = data.get("pubdate", 0)
                pubtime_str = datetime.fromtimestamp(pubdate, SGT).strftime("%Y-%m-%d %H:%M:%S") if pubdate else ""

                return {
                    "采集时间": now_str,
                    "BV号": bvid,
                    "标题": data.get("title", ""),
                    "UP主": owner.get("name", ""),
                    "上传时间": pubtime_str,
                    "总播放量": stat.get("view", 0),
                    "点赞数": stat.get("like", 0),
                    "投币数": stat.get("coin", 0),
                    "收藏数": stat.get("favorite", 0),
                    "转发数": stat.get("share", 0),
                    "评论数": stat.get("reply", 0),
                    "弹幕数": stat.get("danmaku", 0),
                    "在线人数": 0
                }
    except Exception as e:
        print(f"❌ [{bvid}] 请求异常: {e}")

    return {
        "采集时间": now_str, "BV号": bvid, "标题": "获取失败", "UP主": "-", "上传时间": "",
        "总播放量": 0, "点赞数": 0, "投币数": 0, "收藏数": 0, "转发数": 0, "评论数": 0, "弹幕数": 0, "在线人数": 0
    }

def build_summary_sheet(df_half):
    """根据最新数据构建 Sheet 1: 综合分析汇总"""
    latest = df_half.sort_values("采集时间").groupby("BV号", as_index=False).last()
    first = df_half.sort_values("采集时间").groupby("BV号", as_index=False).first()
    first_views = dict(zip(first["BV号"], first["总播放量"]))
    
    summary_rows = []
    # 头部固定 6 行说明
    desc_headers = [
        ["加权综合得分", "公式：(转发*5 + 收藏*3 + 评论*3 + 投币*2 + 弹幕*1 + 点赞*1) / 播放量。反映视频综合推流潜力。"],
        ["币赞比", "投币/点赞。>15%说明内容极硬核；反映粉丝忠诚度和内容深度。"],
        ["播放评论比", "播放量/评论数。数值越小（如50）代表互动意愿越强，视频更具讨论度。"],
        ["收藏点赞比", "收藏/点赞。>1代表工具属性强（先存后看）；<0.5代表纯娱乐属性。"],
        ["", ""],
        ["", ""]
    ]
    for row in desc_headers:
        summary_rows.append({col: (row[idx] if idx < len(row) else "") for idx, col in enumerate(["BV号", "UP主"])})
        
    for _, r in latest.iterrows():
        bvid = r["BV号"]
        v = r["总播放量"]
        l = r["点赞数"]
        c = r["投币数"]
        f = r["收藏数"]
        s = r["转发数"]
        rep = r["评论数"]
        d = r["弹幕数"]
        
        init_v = first_views.get(bvid, v)
        inc_v = v - init_v
        
        score = round((s*5 + f*3 + rep*3 + c*2 + d*1 + l*1) / v, 4) if v > 0 else 0
        like_rate = f"{(l/v*100):.2f}%" if v > 0 else "0%"
        fav_rate = f"{(f/v*100):.2f}%" if v > 0 else "0%"
        coin_rate = f"{(c/v*100):.2f}%" if v > 0 else "0%"
        rep_rate = f"{(rep/v*100):.2f}%" if v > 0 else "0%"
        dan_rate = f"{(d/v*100):.2f}%" if v > 0 else "0%"
        share_rate = f"{(s/v*100):.2f}%" if v > 0 else "0%"
        coin_like = f"{(c/l*100):.2f}%" if l > 0 else "0%"
        view_rep = f"{(v/rep):.1f}:1" if rep > 0 else "-"
        
        summary_rows.append({
            "BV号": bvid, "UP主": r["UP主"], "标题": r["标题"], "上传时间": r["上传时间"],
            "总播放": v, "今日增量": inc_v, "加权质量得分": score, "建议评分": "爆火潜力",
            "当前在线": r["在线人数"], "点赞率": like_rate, "收藏率": fav_rate, "投币率": coin_rate,
            "评论率": rep_rate, "弹幕率": dan_rate, "转发率": share_rate, "币赞比": coin_like, "播放评论比": view_rep
        })
        
    df_sum = pd.DataFrame(summary_rows)
    columns = list(df_sum.columns)
    columns[0] = "指标"
    columns[1] = "解读"
    df_sum.columns = columns
    return df_sum

def run_once():
    now_sgt = datetime.now(SGT)
    print(f"🚀 开始采集 Bilibili 数据 (时间: {now_sgt.strftime('%Y-%m-%d %H:%M:%S')})")
    
    bvs = load_bv_list()
    if not bvs:
        print("❌ BV 列表为空，退出。")
        return

    new_data = []
    for bvid in bvs:
        print(f"正在抓取: {bvid} ...")
        item = fetch_bilibili_api(bvid, SESSDATA)
        new_data.append(item)
        time.sleep(1)

    new_df = pd.DataFrame(new_data)
    date_str = now_sgt.strftime("%Y%m%d")
    excel_path = os.path.join(BASE_DIR, f"bilibili_{date_str}_report.xlsx")

    if os.path.exists(excel_path):
        try:
            old_half = pd.read_excel(excel_path, sheet_name="3. 半小时间隔明细")
            df_half = pd.concat([old_half, new_df], ignore_index=True)
        except Exception:
            df_half = new_df
    else:
        df_half = new_df

    # 计算增量与格式化
    df_half["采集时间"] = pd.to_datetime(df_half["采集时间"])
    df_half = df_half.sort_values(["BV号", "采集时间"]).reset_index(drop=True)
    df_half["时段播放增量"] = df_half.groupby("BV号")["总播放量"].diff().fillna(0).astype(int)
    df_half["采集时间"] = df_half["采集时间"].dt.strftime("%Y-%m-%d %H:%M:%S")

    # 生成一小时间隔明细（筛选整点数据）
    df_half_dt = df_half.copy()
    df_half_dt["dt"] = pd.to_datetime(df_half_dt["采集时间"])
    df_hourly = df_half_dt[df_half_dt["dt"].dt.minute == 0].drop(columns=["dt"]).reset_index(drop=True)
    if df_hourly.empty:
        df_hourly = df_half.copy()

    # 构建汇总 Sheet 1
    df_summary = build_summary_sheet(df_half)

    # 写入 Excel（仅包含 3 个 Sheet）
    with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
        df_summary.to_excel(writer, sheet_name="1. 综合分析汇总", index=False)
        df_hourly.to_excel(writer, sheet_name="2. 一小时间隔明细", index=False)
        df_half.to_excel(writer, sheet_name="3. 半小时间隔明细", index=False)

    print(f"✅ 成功写入 3 个 Sheet 并保存至: {excel_path}")

if __name__ == "__main__":
    run_once()
