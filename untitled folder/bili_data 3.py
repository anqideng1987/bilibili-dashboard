import re
import sys
import time
import requests
import pandas as pd
from datetime import datetime, time as dtime, timedelta
from urllib.parse import urlparse, parse_qs
import os

API_VIEW = "https://api.bilibili.com/x/web-interface/view"
API_ONLINE = "https://api.bilibili.com/x/player/online/total"
API_FAV_LIST = "https://api.bilibili.com/x/v3/fav/resource/list"

def fetch_fav_bvs(media_id: str, session: requests.Session) -> list:
    """自动翻页获取B站收藏夹内的所有视频BV号"""
    bvs = []
    page = 1
    print(f"正在获取收藏夹 [{media_id}] 的全部视频列表...")
    while True:
        params = {
            "media_id": media_id,
            "pn": page,
            "ps": 20,
            "platform": "web"
        }
        try:
            r = session.get(API_FAV_LIST, params=params, headers=_headers(), timeout=15)
            r.raise_for_status()
            data = r.json()
            if data.get("code") != 0:
                print(f"获取收藏夹失败: {data.get('message')}")
                break
            
            medias = data.get("data", {}).get("medias")
            if not medias:
                break
                
            for m in medias:
                bvid = m.get("bvid")
                if bvid:
                    bvs.append(bvid)
            
            has_more = data.get("data", {}).get("has_more", False)
            if not has_more or len(medias) == 0:
                break
            page += 1
            time.sleep(0.3)
        except Exception as e:
            print(f"请求收藏夹出错: {e}")
            break
    print(f"收藏夹 [{media_id}] 解析完成，共找到 {len(bvs)} 个视频。")
    return bvs

def normalize_to_bvid(s: str) -> str:
    s = (s or "").strip()
    if not s: raise ValueError("输入为空")
    if re.fullmatch(r"(BV[0-9A-Za-z]+)", s): return s
    m = re.search(r"/video/(BV[0-9A-Za-z]+)/?", s)
    if m: return m.group(1)
    qs = parse_qs(urlparse(s).query)
    if "bvid" in qs and qs["bvid"]: return qs["bvid"][0]
    raise ValueError(f"无法解析BV号: {s}")

def read_inputs_from_file(path: str, session: requests.Session) -> list:
    items = []
    if not os.path.exists(path): return []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            
            ml_id = None
            if "fid=" in line:
                qs = parse_qs(urlparse(line).query)
                if "fid" in qs: ml_id = qs["fid"][0]
            elif "ml" in line:
                m_ml = re.search(r"ml([0-9]+)", line)
                if m_ml: ml_id = m_ml.group(1)
            elif re.fullmatch(r"ml[0-9]+", line):
                ml_id = line[2:]
            elif re.fullmatch(r"[0-9]+", line):
                ml_id = line

            if ml_id:
                fav_bvs = fetch_fav_bvs(ml_id, session)
                items.extend(fav_bvs)
            else:
                items.append(line)
    return items

def validate_all_inputs(path: str, session: requests.Session):
    print(f"=== 开始预检输入文件 [{path}] ===")
    if not os.path.exists(path):
        print(f"提示: 输入文件 {path} 不存在。")
        return
    
    with open(path, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip() and not line.startswith("#")]
    
    if not lines:
        print("提示: 输入文件内容为空。")
        return

    for idx, line in enumerate(lines):
        try:
            ml_id = None
            if "fid=" in line:
                qs = parse_qs(urlparse(line).query)
                if "fid" in qs: ml_id = qs["fid"][0]
            elif "ml" in line:
                m_ml = re.search(r"ml([0-9]+)", line)
                if m_ml: ml_id = m_ml.group(1)
            elif re.fullmatch(r"ml[0-9]+", line):
                ml_id = line[2:]
            elif re.fullmatch(r"[0-9]+", line):
                ml_id = line

            if ml_id:
                test_r = session.get(API_FAV_LIST, params={"media_id": ml_id, "pn": 1, "ps": 1, "platform": "web"}, headers=_headers(), timeout=10)
                test_data = test_r.json()
                if test_data.get("code") != 0:
                    print(f"  [预检警告] 第 {idx+1} 行收藏夹/ID [{line}] 验证失败: {test_data.get('message')}")
                else:
                    print(f"  [预检通过] 第 {idx+1} 行收藏夹 [{ml_id}] 有效。")
            else:
                bvid = normalize_to_bvid(line)
                print(f"  [预检通过] 第 {idx+1} 行单视频 [{bvid}] 格式正确。")
        except Exception as e:
            print(f"  [预检错误] 第 {idx+1} 行输入 [{line}] 无法识别或请求失败: {e}")
    print("=== 预检结束 ===\n")

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

def save_csv_append(csv_path: str, rows: list) -> pd.DataFrame:
    df_new = pd.DataFrame(rows)
    if os.path.exists(csv_path):
        df_existing = pd.read_csv(csv_path, encoding="utf-8-sig")
        # 兼容老数据可能没有原始顺序字段的情况
        if "原始顺序" not in df_existing.columns:
            df_existing["原始顺序"] = 0
        df_combined = pd.concat([df_existing, df_new], ignore_index=True)
    else:
        df_combined = df_new
    
    # 【修复】去重条件加入 原始顺序，防止重复/相同BV号在同一时间被过滤吞掉
    if "采集时间" in df_combined.columns and "BV号" in df_combined.columns and "原始顺序" in df_combined.columns:
        df_combined = df_combined.drop_duplicates(subset=["采集时间", "BV号", "原始顺序"], keep="last")
        
    df_combined.to_csv(csv_path, index=False, encoding="utf-8-sig")
    return df_combined

def generate_daily_report_from_df(csv_path: str, df: pd.DataFrame):
    df["采集时间"] = pd.to_datetime(df["采集时间"])
    if "原始顺序" not in df.columns:
        df["原始顺序"] = 0
    
    # 严格按照 原始顺序 -> 采集时间 排序
    df = df.sort_values(["原始顺序", "采集时间"])
    
    clean_df = df.drop(columns=["输入"], errors="ignore")

    # 1. 针对整点表：联合主键 (原始顺序, BV号) 分组计算增量
    hourly_df = clean_df[clean_df["采集时间"].dt.minute == 0].copy()
    hourly_df["时段播放增量"] = hourly_df.groupby(["原始顺序", "BV号"], sort=False)["总播放量"].diff().fillna(0).astype(int)
    hourly_df = hourly_df.sort_values(["原始顺序", "采集时间"])

    # 2. 针对半小时表：联合主键 (原始顺序, BV号) 分组计算差值
    half_hourly_df = clean_df.copy()
    half_hourly_df["时段播放增量"] = half_hourly_df.groupby(["原始顺序", "BV号"], sort=False)["总播放量"].diff().fillna(0).astype(int)
    half_hourly_df = half_hourly_df.sort_values(["原始顺序", "采集时间"])

    intro_data = [
        {"指标": "加权综合得分", "解读": "公式：(转发*5 + 收藏*3 + 评论*3 + 投币*2 + 弹幕*1 + 点赞*1) / 播放量。反映视频综合推流潜力。"},
        {"指标": "币赞比", "解读": "投币/点赞。>15%说明内容极硬核；反映粉丝忠诚度和内容深度。"},
        {"指标": "播放评论比", "解读": "播放量/评论数。数值越小（如50）代表互动意愿越强，视频更具讨论度。"},
        {"指标": "收藏点赞比", "解读": "收藏/点赞。>1代表工具属性强（先存后看）；<0.5代表纯娱乐属性。"},
        {"指标": "建议评分", "解读": ">0.18: 爆火潜力 | 0.08-0.18: 优质内容 | <0.08: 常规更新。"}
    ]
    intro_df = pd.DataFrame(intro_data)

    combined_rows = []
    # 按照 (原始顺序, BV号) 联合分组遍历
    for key, g in clean_df.groupby(["原始顺序", "BV号"], sort=False):
        last = g.iloc[-1]
        
        latest_date = last["采集时间"].normalize()
        today_g = g[g["采集时间"] >= latest_date]
        
        if not today_g.empty:
            first_today = today_g.iloc[0]
            today_increment = last["总播放量"] - first_today["总播放量"]
        else:
            today_increment = 0

        v = last["总播放量"] if last["总播放量"] > 0 else 1
        w_score = (last["转发数"]*5 + last["收藏数"]*3 + last["评论数"]*3 + last["投币数"]*2 + last["弹幕数"]*1 + last["点赞数"]*1) / v

        combined_rows.append({
            "原始顺序": last["原始顺序"],
            "BV号": last["BV号"],
            "UP主": last["UP主"],
            "标题": last["标题"],
            "上传时间": last["上传时间"],
            "总播放": last["总播放量"],
            "今日增量": today_increment,
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

    paragraph_rows = []
    for key, g in clean_df.groupby(["原始顺序", "BV号"], sort=False):
        meta = g.iloc[-1]
        latest_time = g["采集时间"].max()
        target_date = latest_time.date()
        yesterday_date = target_date - timedelta(days=1)
        
        t_start_ref = datetime.combine(yesterday_date, dtime(19, 50, 0))
        t_end_ref = datetime.combine(target_date, dtime(19, 50, 0))
        
        g_sorted = g.copy()
        g_sorted["start_diff"] = (g_sorted["采集时间"] - t_start_ref).abs()
        g_sorted["end_diff"] = (g_sorted["采集时间"] - t_end_ref).abs()
        
        start_row = g_sorted.loc[g_sorted["start_diff"].idxmin()]
        end_row = g_sorted.loc[g_sorted["end_diff"].idxmin()]
        
        def format_metric(start_v, end_v):
            s = int(start_v)
            e = int(end_v)
            diff = e - s
            pct = (diff / s) if s > 0 else 0.0
            sign = "+" if diff >= 0 else ""
            return f"{s:,} -> {e:,}\n▲ {sign}{diff:,} ({sign}{pct:.1%})"

        report_text = (
            f"📈 【今日数据播报】\n"
            f"截至 {end_row['采集时间'].strftime('%m月%d日 %H:%M')}\n\n"
            f"▶ 播放量\n{format_metric(start_row.get('总播放量',0), end_row.get('总播放量',0))}\n\n"
            f"▶ 点赞\n{format_metric(start_row.get('点赞数',0), end_row.get('点赞数',0))}\n\n"
            f"▶ 投币\n{format_metric(start_row.get('投币数',0), end_row.get('投币数',0))}\n\n"
            f"▶ 收藏\n{format_metric(start_row.get('收藏数',0), end_row.get('收藏数',0))}\n\n"
            f"▶ 转发\n{format_metric(start_row.get('转发数',0), end_row.get('转发数',0))}\n\n"
            f"▶ 评论\n{format_metric(start_row.get('评论数',0), end_row.get('评论数',0))}\n\n"
            f"▶ 弹幕\n{format_metric(start_row.get('弹幕数',0), end_row.get('弹幕数',0))}"
        )

        paragraph_rows.append({
            "原始顺序": meta["原始顺序"],
            "BV号": meta["BV号"],
            "UP主": meta["UP主"],
            "视频标题": meta["标题"],
            "战报文案（可直接复制发微博）": report_text
        })

    paragraph_df = pd.DataFrame(paragraph_rows).sort_values("原始顺序")

    report_xlsx = csv_path.replace(".csv", "_report.xlsx")
    with pd.ExcelWriter(report_xlsx, engine="openpyxl") as writer:
        intro_df.to_excel(writer, index=False, sheet_name="1. 综合分析汇总", startrow=0)
        combined_df.drop(columns=["原始顺序"]).to_excel(writer, index=False, sheet_name="1. 综合分析汇总", startrow=len(intro_df) + 2)
        
        hourly_df.drop(columns=["原始顺序"], errors="ignore").to_excel(writer, index=False, sheet_name="2. 一小时间隔明细")
        half_hourly_df.drop(columns=["原始顺序"], errors="ignore").to_excel(writer, index=False, sheet_name="3. 半小时间隔明细")
        paragraph_df.drop(columns=["原始顺序"]).to_excel(writer, index=False, sheet_name="4. 每日战报文案汇总")
        
        worksheet = writer.sheets["4. 每日战报文案汇总"]
        worksheet.column_dimensions['A'].width = 15
        worksheet.column_dimensions['B'].width = 15
        worksheet.column_dimensions['C'].width = 30
        worksheet.column_dimensions['D'].width = 45
        
        for row in range(2, worksheet.max_row + 1):
            cell = worksheet.cell(row=row, column=4)
            cell.alignment = cell.alignment.copy(wrap_text=True)

    print(f"[{datetime.now().strftime('%H:%M:%S')}] 综合报表已更新。")

def run_collection_task(session, input_path, csv_path):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    items = read_inputs_from_file(input_path, session)
    if not items:
        print(f"[{timestamp}] input.txt 为空，跳过本次采集。")
        return
    
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

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="input.txt")
    args = parser.parse_args()
    session = requests.Session()

    print("=== B站数据监控与定时智能采集脚本已启动 ===")

    validate_all_inputs(args.input, session)

    last_triggered_signature = None

    while True:
        now = datetime.now()
        current_date_str = now.strftime('%Y%m%d')
        csv_path = f"bilibili_{current_date_str}.csv"
        
        minute = now.minute
        hour = now.hour

        is_on_hour = (minute == 0)
        is_on_half = (minute == 30)
        is_target_time = (hour == 19 and minute == 50)

        time_signature = f"{now.strftime('%Y%m%d-%H')}-{minute}"

        if (is_on_hour or is_on_half or is_target_time) and last_triggered_signature != time_signature:
            trigger_reason = "19:50 定时战报节点" if is_target_time else ("整点采集" if is_on_hour else "半点采集")
            print(f"\n--- 触发采集 [{trigger_reason}] 当前时间: {now.strftime('%Y-%m-%d %H:%M:%S')} ---")
            
            validate_all_inputs(args.input, session)
            run_collection_task(session, args.input, csv_path)
            last_triggered_signature = time_signature
            
        time.sleep(10)

if __name__ == "__main__":
    main()