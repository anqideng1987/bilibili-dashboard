import re
import sys
import time
import requests
import pandas as pd
from datetime import datetime
from urllib.parse import urlparse, parse_qs
import os

# B站 API 地址
API_VIEW = "https://api.bilibili.com/x/web-interface/view"
API_ONLINE = "https://api.bilibili.com/x/player/online/total"

# ----------------- 工具函数 -----------------
def normalize_to_bvid(s: str) -> str:
    s = (s or "").strip()
    if not s: raise ValueError("输入为空")
    if re.fullmatch(r"(BV[0-9A-Za-z]+)", s): return s
    m = re.search(r"/video/(BV[0-9A-Za-z]+)/?", s)
    if m: return m.group(1)
    qs = parse_qs(urlparse(s).query)
    if "bvid" in qs and qs["bvid"]: return qs["bvid"][0]
    raise ValueError(f"无法解析BV号: {s}")

def read_inputs_from_file(path: str) -> list[str]:
    items = []
    if not os.path.exists(path): return []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                items.append(line)
    return items

def _headers() -> dict:
    return {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://www.bilibili.com/",
    }

def fetch_video_stats(bvid: str, session: requests.Session) -> dict:
    r = session.get(API_VIEW, params={"bvid": bvid}, headers=_headers(), timeout=15)
    r.raise_for_status()
    payload = r.json()
    if payload.get("code") != 0: raise RuntimeError(payload.get("message"))
    data = payload["data"]
    stat = data.get("stat", {})
    owner = data.get("owner", {})
    
    # 获取上传时间
    pub_ts = data.get("pubdate")
    upload_time = datetime.fromtimestamp(pub_ts).strftime("%Y-%m-%d %H:%M:%S") if pub_ts else "未知"
    
    online_total = 0
    cid = data.get("cid")
    if cid:
        try:
            r2 = session.get(API_ONLINE, params={"bvid": bvid, "cid": cid}, headers=_headers(), timeout=10)
            online_total = r2.json().get("data", {}).get("total", 0)
        except: pass
    return {
        "BV号": bvid,
        "标题": data.get("title"),
        "UP主": owner.get("name"),
        "上传时间": upload_time,
        "总播放量": stat.get("view", 0),
        "点赞数": stat.get("like", 0),
        "投币数": stat.get("coin", 0),
        "收藏数": stat.get("favorite", 0),
        "转发数": stat.get("share", 0),
        "评论数": stat.get("reply", 0),
        "弹幕数": stat.get("danmaku", 0),
        "在线人数": online_total,
    }

def save_csv_append(csv_path: str, rows: list[dict]) -> pd.DataFrame:
    df_new = pd.DataFrame(rows)
    if os.path.exists(csv_path):
        df_existing = pd.read_csv(csv_path, encoding="utf-8-sig")
        df_combined = pd.concat([df_existing, df_new], ignore_index=True)
    else:
        df_combined = df_new
    df_combined.to_csv(csv_path, index=False, encoding="utf-8-sig")
    return df_combined

# ----------------- 核心报表生成 -----------------
def generate_daily_report_from_df(csv_path: str, df: pd.DataFrame):
    df["采集时间"] = pd.to_datetime(df["采集时间"])
    df = df.sort_values(["原始顺序", "采集时间"])
    detail_df = df.drop(columns=["输入"], errors="ignore")
    detail_df["时段播放增量"] = detail_df.groupby("BV号")["总播放量"].diff().fillna(0).astype(int)

    # 1. 构建指标解读说明（作为表格的一部分或独立页）
    intro_data = [
        {"指标": "加权综合得分", "解读": "公式：(转发*5 + 收藏*3 + 评论*3 + 投币*2 + 弹幕*1 + 点赞*1) / 播放量。反映视频综合推流潜力。"},
        {"指标": "币赞比", "解读": "投币/点赞。>15%说明内容极硬核；反映粉丝忠诚度和内容深度。"},
        {"指标": "播放评论比", "解读": "播放量/评论数。数值越小（如50）代表互动意愿越强，视频更具讨论度。"},
        {"指标": "收藏点赞比", "解读": "收藏/点赞。>1代表工具属性强（先存后看）；<0.5代表纯娱乐属性。"},
        {"指标": "建议评分", "解读": ">0.18: 爆火潜力 | 0.08-0.18: 优质内容 | <0.08: 常规更新。"}
    ]
    intro_df = pd.DataFrame(intro_data)

    # 2. 合并后的综合汇总页
    combined_rows = []
    for _, g in detail_df.groupby("BV号", sort=False):
        last = g.iloc[-1]
        first = g.iloc[0]
        v = last["总播放量"] if last["总播放量"] > 0 else 1
        
        # 加权得分计算
        w_score = (last["转发数"]*5 + last["收藏数"]*3 + last["评论数"]*3 + last["投币数"]*2 + last["弹幕数"]*1 + last["点赞数"]*1) / v

        combined_rows.append({
            "原始顺序": last["原始顺序"],
            "UP主": last["UP主"],
            "标题": last["标题"],
            "上传时间": last["上传时间"],
            "总播放": last["总播放量"],
            "今日增量": last["总播放量"] - first["总播放量"],
            "加权质量得分": round(w_score, 4),
            "建议评分": "爆火潜力" if w_score > 0.18 else ("优质内容" if w_score > 0.08 else "常规更新"),
            "当前在线": last["在线人数"],
            "点赞率": f"{(last['点赞数']/v):.2%}",
            "收藏率": f"{(last['收藏数']/v):.2%}",
            "投币率": f"{(last['投币数']/v):.2%}",
            "评论率": f"{(last['评论数']/v):.2%}",
            "弹幕率": f"{(last['弹幕数']/v):.2%}",
            "转发率": f"{(last['转发数']/v):.2%}",
            "币赞比": f"{(last['投币数'] / (last['点赞数'] if last['点赞数'] > 0 else 1)):.2%}",
            "播放评论比": f"{v / (last['评论数'] if last['评论数'] > 0 else 1):.1f}:1"
        })

    combined_df = pd.DataFrame(combined_rows).sort_values("原始顺序")
    report_xlsx = csv_path.replace(".csv", "_report.xlsx")
    
    with pd.ExcelWriter(report_xlsx, engine="openpyxl") as writer:
        # 第一页：指标解读 + 综合汇总
        # 我们先写入解读文字，留出空行，再写入数据
        intro_df.to_excel(writer, index=False, sheet_name="1. 综合分析汇总", startrow=0)
        combined_df.drop(columns=["原始顺序"]).to_excel(writer, index=False, sheet_name="1. 综合分析汇总", startrow=len(intro_df) + 2)
        
        # 第二页：明细
        detail_df.drop(columns=["原始顺序"]).to_excel(writer, index=False, sheet_name="2. 每小时采集明细")
    
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 综合报表已更新。")

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="input.txt")
    parser.add_argument("--interval-min", type=int, default=60)
    args = parser.parse_args()
    session = requests.Session()

    while True:
        now = datetime.now()
        timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
        csv_path = f"bilibili_{now.strftime('%Y%m%d')}.csv"
        items = read_inputs_from_file(args.input)
        if not items:
            time.sleep(10); continue
        
        rows = []
        for index, raw in enumerate(items):
            row = {"采集时间": timestamp, "输入": raw, "原始顺序": index}
            try:
                bvid = normalize_to_bvid(raw)
                stats = fetch_video_stats(bvid, session)
                row.update(stats)
                print(f"OK [{index}] {bvid} - {stats['标题'][:15]}...")
            except Exception as e:
                row.update({"标题": "失败", "错误": str(e)})
                print(f"ERR [{index}] {raw}: {e}")
            rows.append(row)
            time.sleep(0.5)

        df_all = save_csv_append(csv_path, rows)
        generate_daily_report_from_df(csv_path, df_all)
        print(f"休眠 {args.interval_min} 分钟...")
        time.sleep(args.interval_min * 60)

if __name__ == "__main__":
    main()
