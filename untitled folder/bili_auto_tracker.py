import re
import time
import os
import random
from datetime import datetime
import pandas as pd
from DrissionPage import ChromiumPage, ChromiumOptions

# 获取当前脚本所在文件夹的绝对路径
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def get_file_path(filename):
    """确保所有读写的文件都定位在脚本所在的绝对路径下"""
    return os.path.join(BASE_DIR, filename)

def extract_bv_ids(input_data):
    """提取所有以 BV 开头的 12 位字符串，保持出现顺序并去重"""
    if isinstance(input_data, list):
        input_data = " ".join(input_data)
    pattern = r'BV[a-zA-Z0-9]{10}'
    found = re.findall(pattern, input_data)
    seen = set()
    return [x for x in found if not (x in seen or seen.add(x))]

def get_today_excel_filename():
    """根据当前日期动态生成 Excel 文件名"""
    today_str = datetime.now().strftime("%Y%m%d")
    return f"bilibili_{today_str}_report.xlsx"

def get_bilibili_data(bv_list):
    """使用 DrissionPage 抓取 B 站视频实时数据"""
    co = ChromiumOptions()
    co.headless(True)
    co.set_argument('--blink-settings=imagesEnabled=false')
    page = ChromiumPage(co)
    
    results = []
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n==========================================")
    print(f"⏰ [{now_str}] 开始抓取 {len(bv_list)} 个视频的数据")
    print(f"==========================================")
    
    try:
        page.get("https://www.bilibili.com/")
        time.sleep(1.5)
        
        for idx, bvid in enumerate(bv_list, start=1):
            url = f"https://www.bilibili.com/video/{bvid}"
            try:
                page.get(url)
                time.sleep(random.uniform(1.0, 1.8))
                
                res = page.run_js("""
                    let data = window.__INITIAL_STATE__ || {};
                    let videoData = data.videoData || {};
                    let stat = videoData.stat || {};
                    let pageTitle = document.title || "";
                    let isInvalid = pageTitle.includes("出错啦") || pageTitle.includes("视频去哪了呢") || !videoData.title;
                    
                    return {
                        is_valid: !isInvalid,
                        title: videoData.title || pageTitle,
                        owner: (videoData.owner && videoData.owner.name) || "",
                        pubdate_ts: videoData.pubdate || 0,
                        view: stat.view || 0,
                        like: stat.like || 0,
                        coin: stat.coin || 0,
                        favorite: stat.favorite || 0,
                        share: stat.share || 0,
                        reply: stat.reply || 0,
                        danmaku: stat.danmaku || 0,
                        online: stat.his_rank || 0
                    };
                """)
                
                if res and res.get("is_valid"):
                    pub_ts = res.get("pubdate_ts", 0)
                    pubdate_str = datetime.fromtimestamp(pub_ts).strftime("%Y-%m-%d %H:%M:%S") if pub_ts else ""
                    
                    results.append({
                        "采集时间": now_str,
                        "BV号": bvid,
                        "标题": res.get("title", ""),
                        "UP主": res.get("owner", ""),
                        "上传时间": pubdate_str,
                        "总播放量": res.get("view", 0),
                        "点赞数": res.get("like", 0),
                        "投币数": res.get("coin", 0),
                        "收藏数": res.get("favorite", 0),
                        "转发数": res.get("share", 0),
                        "评论数": res.get("reply", 0),
                        "弹幕数": res.get("danmaku", 0),
                        "在线人数": res.get("online", 0)
                    })
                    print(f"  └─ [{idx}/{len(bv_list)}] ✅ {bvid} | 播放量: {res.get('view', 0):,}")
            except Exception as e:
                print(f"  └─ [{idx}/{len(bv_list)}] ❌ 抓取失败 {bvid}: {e}")
    finally:
        page.quit()
        
    return pd.DataFrame(results)

def sort_by_bv_order_and_time(df, bv_order, time_col="采集时间"):
    """辅助函数：按 txt 中的 BV 顺序优先排序，次要按时间正序排序"""
    if df.empty or "BV号" not in df.columns:
        return df
    
    # 动态构建 BV 排序权重分类
    unique_bvs_in_df = df["BV号"].unique().tolist()
    # 确保不在 txt 中的历史 BV 也能排在后面
    full_bv_order = bv_order + [b for b in unique_bvs_in_df if b not in bv_order]
    
    bv_cat = pd.CategoricalDtype(categories=full_bv_order, ordered=True)
    df["_bv_sort"] = df["BV号"].astype(bv_cat)
    
    sort_cols = ["_bv_sort"]
    ascending_list = [True]
    
    if time_col and time_col in df.columns:
        df["_time_sort"] = pd.to_datetime(df[time_col])
        sort_cols.append("_time_sort")
        ascending_list.append(True)
        
    df = df.sort_values(by=sort_cols, ascending=ascending_list).drop(columns=["_bv_sort", "_time_sort"], errors="ignore")
    return df

def update_excel_file(df_new_records, bv_order):
    """自动读写对应 Excel 文件，追加数据并按指定的 BV 顺序和时间排序"""
    if df_new_records.empty:
        print("⚠️ 未抓取到新数据，跳过 Excel 更新。")
        return

    target_excel = get_file_path(get_today_excel_filename())

    df_rules = pd.DataFrame([
        {"指标": "加权综合得分", "解读": "公式：(转发*5 + 收藏*3 + 评论*3 + 投币*2 + 弹幕*1 + 点赞*1) / 播放量。反映视频综合推流潜力。"},
        {"指标": "币赞比", "解读": "投币/点赞。>15%说明内容极硬核；反映粉丝忠诚度和内容深度。"},
        {"指标": "播放评论比", "解读": "播放量/评论数。数值越小（如50）代表互动意愿越强，视频更具讨论度。"},
        {"指标": "收藏点赞比", "解读": "收藏/点赞。>1代表工具属性强（先存后看）；<0.5代表纯娱乐属性。"}
    ])

    if os.path.exists(target_excel):
        print(f"📖 正在追加写入今天的数据文件: {target_excel}")
        df_h1 = pd.read_excel(target_excel, sheet_name='2. 一小时间隔明细')
        df_h05 = pd.read_excel(target_excel, sheet_name='3. 半小时间隔明细')
    else:
        print(f"📄 检测到今日新文件，正在自动新建: {target_excel}")
        df_h1 = pd.DataFrame(columns=[
            "采集时间", "BV号", "标题", "UP主", "上传时间", 
            "总播放量", "点赞数", "投币数", "收藏数", "转发数", 
            "评论数", "弹幕数", "在线人数", "时段播放增量"
        ])
        df_h05 = df_h1.copy()

    for _, row in df_new_records.iterrows():
        bvid = row["BV号"]
        
        bvid_h1_history = df_h1[df_h1["BV号"] == bvid]
        last_view_h1 = bvid_h1_history.iloc[-1]["总播放量"] if not bvid_h1_history.empty else row["总播放量"]
        row_h1 = row.copy()
        row_h1["时段播放增量"] = max(0, row["总播放量"] - last_view_h1)
        df_h1 = pd.concat([df_h1, pd.DataFrame([row_h1])], ignore_index=True)
        
        bvid_h05_history = df_h05[df_h05["BV号"] == bvid]
        last_view_h05 = bvid_h05_history.iloc[-1]["总播放量"] if not bvid_h05_history.empty else row["总播放量"]
        row_h05 = row.copy()
        row_h05["时段播放增量"] = max(0, row["总播放量"] - last_view_h05)
        df_h05 = pd.concat([df_h05, pd.DataFrame([row_h05])], ignore_index=True)

    summary_list = []
    copywriting_list = []
    
    for bvid, group in df_h1.groupby("BV号"):
        group["采集时间_dt"] = pd.to_datetime(group["采集时间"])
        group = group.sort_values(by="采集时间_dt")
        
        latest = group.iloc[-1]
        base = group.iloc[0]
        
        v = max(latest["总播放量"], 1)
        l = max(latest["点赞数"], 1)
        r = max(latest["评论数"], 1)
        
        score = (latest["转发数"]*5 + latest["收藏数"]*3 + latest["评论数"]*3 + 
                 latest["投币数"]*2 + latest["弹幕数"]*1 + latest["点赞数"]*1) / v
                 
        rating = "爆火潜力" if score > 0.18 else ("优质内容" if score >= 0.08 else "常规更新")
        
        summary_list.append({
            "BV号": bvid,
            "UP主": latest["UP主"],
            "标题": latest["标题"],
            "上传时间": latest["上传时间"],
            "总播放": latest["总播放量"],
            "今日增量": latest["总播放量"] - base["总播放量"],
            "加权质量得分": round(score, 4),
            "建议评分": rating,
            "当前在线": latest["在线人数"],
            "点赞率": f"{(latest['点赞数']/v):.2%}",
            "收藏率": f"{(latest['收藏数']/v):.2%}",
            "投币率": f"{(latest['投币数']/v):.2%}",
            "评论率": f"{(latest['评论数']/v):.2%}",
            "弹幕率": f"{(latest['弹幕数']/v):.2%}",
            "转发率": f"{(latest['转发数']/v):.2%}",
            "币赞比": f"{(latest['投币数']/l):.2%}",
            "播放评论比": f"{(v/r):.1f}:1"
        })
        
        def fmt_diff(cur, base_val):
            diff = cur - base_val
            pct = (diff / base_val * 100) if base_val > 0 else 0
            return f"{base_val:,} -> {cur:,}\n▲ +{diff:,} (+{pct:.1f}%)" if diff >= 0 else f"{base_val:,} -> {cur:,}\n▼ {diff:,} ({pct:.1f}%)"

        dt_str = pd.to_datetime(latest['采集时间']).strftime('%m月%d日 %H:%M')
        text = (
            f"📈 【今日数据播报】\n截至 {dt_str}\n\n"
            f"▶ 播放量\n{fmt_diff(latest['总播放量'], base['总播放量'])}\n\n"
            f"▶ 点赞\n{fmt_diff(latest['点赞数'], base['点赞数'])}\n\n"
            f"▶ 投币\n{fmt_diff(latest['投币数'], base['投币数'])}\n\n"
            f"▶ 收藏\n{fmt_diff(latest['收藏数'], base['收藏数'])}\n\n"
            f"▶ 转发\n{fmt_diff(latest['转发数'], base['转发数'])}\n\n"
            f"▶ 评论\n{fmt_diff(latest['评论数'], base['评论数'])}\n\n"
            f"▶ 弹幕\n{fmt_diff(latest['弹幕数'], base['弹幕数'])}"
        )
        copywriting_list.append({
            "BV号": bvid,
            "UP主": latest["UP主"],
            "视频标题": latest["标题"],
            "战报文案（可直接复制发微博）": text
        })

    df_summary = pd.DataFrame(summary_list)
    df_copywriting = pd.DataFrame(copywriting_list)
    
    # 对所有 DataFrame 进行统一的 BV 顺序 & 时间正序排序
    df_summary = sort_by_bv_order_and_time(df_summary, bv_order, time_col=None)
    df_h1 = sort_by_bv_order_and_time(df_h1, bv_order, time_col="采集时间")
    df_h05 = sort_by_bv_order_and_time(df_h05, bv_order, time_col="采集时间")
    df_copywriting = sort_by_bv_order_and_time(df_copywriting, bv_order, time_col=None)

    with pd.ExcelWriter(target_excel, engine='openpyxl') as writer:
        df_rules.to_excel(writer, sheet_name='1. 综合分析汇总', index=False, startrow=0)
        df_summary.to_excel(writer, sheet_name='1. 综合分析汇总', index=False, startrow=7)
        df_h1.to_excel(writer, sheet_name='2. 一小时间隔明细', index=False)
        df_h05.to_excel(writer, sheet_name='3. 半小时间隔明细', index=False)
        df_copywriting.to_excel(writer, sheet_name='4. 每日战报文案汇总', index=False)

    print(f"🎉 报表更新完毕: {target_excel}")

def start_hourly_loop():
    txt_file = get_file_path("bv_list.txt")
    INTERVAL_SECONDS = 3600
    
    print("🚀 Bilibili 自动循环抓取与报表生成服务已启动！")
    
    while True:
        if os.path.exists(txt_file):
            with open(txt_file, "r", encoding="utf-8") as f:
                bvs = extract_bv_ids(f.read())
        else:
            print(f"⚠️ 找不到 {txt_file}，请创建该文件并填入 BV 号。")
            bvs = []
            
        if bvs:
            df_new = get_bilibili_data(bvs)
            update_excel_file(df_new, bv_order=bvs)
        else:
            print("⚠️ 未找到有效 BV 号，跳过本次抓取。")
            
        next_run_str = datetime.fromtimestamp(time.time() + INTERVAL_SECONDS).strftime("%H:%M:%S")
        print(f"\n💤 本轮抓取结束。下一次抓取将在 [{next_run_str}] 开始...")
        time.sleep(INTERVAL_SECONDS)

if __name__ == "__main__":
    start_hourly_loop()