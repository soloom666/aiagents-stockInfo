#!/usr/bin/env python3
"""
搜索中化供应链平台招投标/非招投标公告中「保安」「安保」关键词。
平台: https://scm.esinochem.com

用法:
  1. 登录 https://scm.esinochem.com 后从浏览器开发者工具复制 _oo_s cookie
  2. 设置环境变量 ESINOCHEM_COOKIE 或直接修改下方 COOKIE
  3. 运行: python check_notice.py
"""

import requests
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone

# 添加项目根目录到 sys.path，确保能导入 aitrader 模块
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from aitrader.common.emailSendFiles import emailSendContent

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# ============================================================
# 配置
# ============================================================
# Cookie 有效期短，过期后需重新从浏览器复制
COOKIE = "_oo_s=rum=1&id=a9fe58c0-f750-4698-a41e-de0658826286&created=1781422895953&expire=1781423827554&logs=1"

KEYWORDS = ["保安", "安保"]
DAYS_BACK = 15

# 公告类型 — 两个 curl 命令中都是 Bid，猜测非招投标可能是空或 Other
# 若实际 plateType 不同，修改此配置
PLATE_TYPES = {
    "招投标公告": "Bid",
    "非招投标公告": "",          # 空字符串表示不过滤 plateType
}

BASE_URL = "https://scm.esinochem.com"
API_PATH = "/gateway/obs/business/notice/outer/page/queryPageList"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Content-Type": "application/json",
    "Cookie": COOKIE,
    "Referer": f"{BASE_URL}/",
}
PROXY = {"http": None, "https": None}

OUTPUT_FILE = "notice.json"  # 相对于脚本所在目录


def date_range():
    """返回最近 DAYS_BACK 天的日期范围"""
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=DAYS_BACK)
    return start, end


def search_plate(keyword, plate_type, start_dt, end_dt):
    """
    按公告类型和关键词搜索。
    plate_type: "Bid" = 招投标, "" = 全部（非招投标）
    返回 [(title, url, auditDate, plateType), ...]
    """
    body = {
        "start": 0,
        "limit": 10,
        "currentPage": 1,
        "model": {
            "noticeType": "01",
            "state": "",
            "title": keyword,
            "auditDate": [
                start_dt.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                end_dt.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            ],
            "queryBeginTime": start_dt.strftime("%Y-%m-%d"),
            "queryEndTime": end_dt.strftime("%Y-%m-%d"),
            "plateType": plate_type,
        },
    }

    try:
        url = f"{BASE_URL}{API_PATH}?t={int(time.time() * 1000)}"
        resp = requests.post(
            url,
            json=body,
            headers=HEADERS,
            timeout=20,
            proxies=PROXY,
        )
        resp.raise_for_status()
        data = resp.json()
    except requests.exceptions.RequestException as e:
        print(f"  [ERROR] 请求失败: {e}", file=sys.stderr)
        return []
    except json.JSONDecodeError:
        print(f"  [ERROR] 响应非 JSON: {resp.text[:300]}", file=sys.stderr)
        return []

    if not data.get("status"):
        print(f"  [ERROR] API 返回失败: {data.get('msg', data.get('message', str(data)[:200]))}", file=sys.stderr)
        return []

    rows = data.get("data", {}).get("root", [])
    results = []
    for row in rows:
        results.append({
            "title": row.get("title", ""),
            "url": f"{BASE_URL}/#/noticeDetail?id={row.get('noticeId', '')}",
            "auditDate": row.get("startTime", ""),
            "plateType": row.get("plateTypeName", plate_type),
        })
    return results


def load_old_results():
    """加载上一次查询的 notice.json，不存在则返回 None"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(script_dir, OUTPUT_FILE)
    if not os.path.exists(output_path):
        return None
    with open(output_path, "r", encoding="utf-8") as f:
        return json.load(f)


def extract_notice_map(data):
    """从结果数据中提取 noticeId -> item 的映射"""
    notice_map = {}
    for plate_label, kw_results in data.get("results", {}).items():
        for kw, items in kw_results.items():
            for item in items:
                nid = item["url"].split("id=")[-1] if "id=" in item["url"] else ""
                if nid:
                    notice_map[nid] = item
    return notice_map


def compare_and_notify(old_data, new_data):
    """对比新旧数据，有变化则发送邮件通知"""
    old_map = extract_notice_map(old_data)
    new_map = extract_notice_map(new_data)

    new_ids = set(new_map.keys()) - set(old_map.keys())
    removed_ids = set(old_map.keys()) - set(new_map.keys())

    if not new_ids and not removed_ids:
        print("📭 公告无变化，不发送邮件")
        return

    lines = ["【中化供应链平台 - 保安/安保公告变化提醒】\n"]
    lines.append(f"查询时间: {new_data['queryTime']}")
    lines.append(f"日期范围: {new_data['dateRange']['start']} ~ {new_data['dateRange']['end']}")
    lines.append(f"公告总数: {old_data['totalFound']} → {new_data['totalFound']}\n")

    if new_ids:
        lines.append(f"--- 新增公告 ({len(new_ids)} 条) ---")
        for nid in sorted(new_ids, key=lambda x: new_map[x].get("auditDate", ""), reverse=True):
            item = new_map[nid]
            date_str = item['auditDate'][:10] if item['auditDate'] else 'N/A'
            lines.append(f"  [{date_str}] {item['title']}")
            lines.append(f"  链接: {item['url']}\n")

    if removed_ids:
        lines.append(f"--- 已移除公告 ({len(removed_ids)} 条) ---")
        for nid in removed_ids:
            item = old_map[nid]
            date_str = item['auditDate'][:10] if item['auditDate'] else 'N/A'
            lines.append(f"  [{date_str}] {item['title']}")
            lines.append(f"  链接: {item['url']}\n")

    lines.append("---")
    lines.append("系统邮件请勿回复。")

    content = "\n".join(lines)
    print(f"\n📧 检测到公告变化，发送邮件...")
    success = emailSendContent(content, title="中化供应链平台 保安/安保公告变化提醒")
    if success:
        print("✅ 邮件发送成功")
    else:
        print("❌ 邮件发送失败")


def main():
    start_dt, end_dt = date_range()

    print(f"查询时间范围: {start_dt.strftime('%Y-%m-%d')} ~ {end_dt.strftime('%Y-%m-%d')}")
    print(f"关键词: {', '.join(KEYWORDS)}")
    print("=" * 60)

    all_results = {}  # plate_type_label -> {keyword: [items]}
    seen_ids = set()  # 跨分类去重

    for plate_label, plate_type in PLATE_TYPES.items():
        print(f"\n{'='*60}")
        print(f"【{plate_label}】(plateType={plate_type!r})")
        print(f"{'='*60}")

        all_results[plate_label] = {}
        for kw in KEYWORDS:
            print(f"  搜索「{kw}」...")
            items = search_plate(kw, plate_type, start_dt, end_dt)
            # 去重: 若公告已在其他分类出现则跳过
            deduped = []
            for item in items:
                nid = item["url"].split("id=")[-1] if "id=" in item["url"] else ""
                if nid not in seen_ids:
                    seen_ids.add(nid)
                    deduped.append(item)
            all_results[plate_label][kw] = deduped
            print(f"    → 找到 {len(deduped)} 条")

    # ---- 打印结果 ----
    print("\n\n" + "=" * 60)
    print("📋 结果汇总")
    print("=" * 60)

    total_found = 0
    for plate_label, kw_results in all_results.items():
        for kw, items in kw_results.items():
            if items:
                total_found += len(items)
                print(f"\n【{plate_label}】「{kw}」— {len(items)} 条:")
                for i, item in enumerate(items, 1):
                    print(f"  {i}. {item['title']}")
                    print(f"     日期: {item['auditDate'][:10] if item['auditDate'] else 'N/A'}")
                    print(f"     链接: {item['url']}")

    if total_found == 0:
        print("\n😔 最近 15 天没有找到「保安」「安保」相关公告。")

    # ---- 加载旧数据用于对比 ----
    old_data = load_old_results()

    # ---- 写入 notice.json ----
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(script_dir, OUTPUT_FILE)

    output_data = {
        "queryTime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "dateRange": {
            "start": start_dt.strftime("%Y-%m-%d"),
            "end": end_dt.strftime("%Y-%m-%d"),
        },
        "keywords": KEYWORDS,
        "totalFound": total_found,
        "results": all_results,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    print(f"\n✅ 结果已写入: {output_path}")

    # ---- 对比变化并发送邮件 ----
    if old_data is not None:
        compare_and_notify(old_data, output_data)
    else:
        print("📝 首次运行，已保存 notice.json，无历史数据可对比")

    return total_found


if __name__ == "__main__":
    count = main()
    sys.exit(0 if count > 0 else 1)
