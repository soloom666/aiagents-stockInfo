#!/usr/bin/env python3
"""
检查浦东公租房平台房源：航头镇 + 两室
页面: https://select.pdgzf.com/houseLists

typeName 映射:
  "1" = 一室  "2" = 两室  "3" = 三室  "4" = 四室
"""
import requests
import json
import os
import sys
import time
from datetime import datetime

# 添加项目根目录到 sys.path，确保能导入 aitrader 模块
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from aitrader.common.emailSendFiles import emailSendContent

# 修复 Windows GBK 控制台编码问题
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# 配置
TOWN = "航头镇"
ROOM_TYPE = "2"        # 2 = 两室
ROOM_TYPE_NAME = "两室"

BASE_URL = "https://select.pdgzf.com"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Content-Type": "application/json",
    "Referer": f"{BASE_URL}/houseLists",
}

# 公司代理可能导致连接失败，禁用它
PROXY = {"http": None, "https": None}

OUTPUT_FILE = "house.json"  # 相对于脚本所在目录


def get_output_path():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), OUTPUT_FILE)


def api_post(path, body, timeout=15):
    """POST 请求，返回 JSON data 或 None"""
    try:
        resp = requests.post(
            f"{BASE_URL}{path}",
            json=body,
            headers=HEADERS,
            timeout=timeout,
            proxies=PROXY,
        )
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] API 请求失败: {path} - {e}", file=sys.stderr)
        return None


def find_town_project_id(town_name):
    """从项目列表中查找指定街道的项目 ID"""
    data = api_post(
        "/api/v1.0/app/gzf/project/list",
        {"QueryJson": {"Type": 1}, "pageSize": 200},
    )
    if not data or "data" not in data:
        return None

    projects = data["data"].get("data", [])
    for p in projects:
        tn = p.get("townshipName") or ""
        area_name = (p.get("area") or {}).get("areaName") or ""
        if town_name in tn or town_name in area_name:
            return {
                "id": p["id"],
                "apiId": p.get("apiId"),
                "name": p.get("name"),
                "houseCount": p.get("houseCount"),
                "rentableCount": p.get("rentableCount"),
            }
    return None


def check_house_count(project_id, room_type):
    """查询指定项目和户型的可租房源数量"""
    body = {
        "where": {
            "keywords": "",
            "township": None,
            "projectId": project_id,
            "typeName": room_type,
            "rent": None,
        },
        "pageIndex": 0,
        "pageSize": 10,
    }
    data = api_post("/api/v1.0/app/gzf/house/list", body)
    if not data or "data" not in data:
        return 0, []

    total = data["data"].get("totalCount", 0)
    items = data["data"].get("data", [])
    return total, items


def send_notification(message):
    """发送通知 — 通过邮件推送"""
    print("=" * 50)
    print(message)
    print("=" * 50)


def load_old_results():
    """加载上一次查询的 house.json，不存在则返回 None"""
    path = get_output_path()
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def extract_house_map(data):
    """从结果数据中提取 fullName -> item 的映射"""
    house_map = {}
    for item in data.get("houses", []):
        name = item.get("fullName", "")
        if name:
            house_map[name] = item
    return house_map


def compare_and_notify(old_data, new_data):
    """对比新旧数据，有变化则发送邮件通知"""
    old_map = extract_house_map(old_data)
    new_map = extract_house_map(new_data)

    new_names = set(new_map.keys()) - set(old_map.keys())
    removed_names = set(old_map.keys()) - set(new_map.keys())
    count_changed = old_data["targetCount"] != new_data["targetCount"]
    rentable_changed = old_data.get("project", {}).get("rentableCount") != new_data.get("project", {}).get("rentableCount")

    if not new_names and not removed_names and not count_changed and not rentable_changed:
        print("📭 房源无变化，不发送邮件")
        return

    lines = ["【浦东公租房 - 房源变化提醒】\n"]
    lines.append(f"查询时间: {new_data['queryTime']}")
    lines.append(f"区域: {new_data['town']}  户型: {new_data['roomType']}")
    lines.append(f"项目: {new_data['project']['name']}\n")

    if rentable_changed:
        old_r = old_data.get("project", {}).get("rentableCount", 0)
        new_r = new_data.get("project", {}).get("rentableCount", 0)
        lines.append(f"项目可租房源: {old_r} → {new_r}")

    if count_changed:
        lines.append(f"目标户型可租: {old_data['targetCount']} → {new_data['targetCount']}")
    lines.append("")

    if new_names:
        lines.append(f"--- 新增房源 ({len(new_names)} 套) ---")
        for name in sorted(new_names):
            item = new_map[name]
            area = item.get('rentalArea', 'N/A')
            floor = item.get('floorName', 'N/A')
            toward = item.get('toward', 'N/A')
            lines.append(f"  {name}")
            lines.append(f"  面积: {area}m²  楼层: {floor}  朝向: {toward}\n")

    if removed_names:
        lines.append(f"--- 已下架房源 ({len(removed_names)} 套) ---")
        for name in sorted(removed_names):
            item = old_map[name]
            area = item.get('rentalArea', 'N/A')
            floor = item.get('floorName', 'N/A')
            toward = item.get('toward', 'N/A')
            lines.append(f"  {name}")
            lines.append(f"  面积: {area}m²  楼层: {floor}  朝向: {toward}\n")

    if new_data["targetCount"] > 0:
        lines.append(f"👉 详情链接: {BASE_URL}/houseLists")

    lines.append("\n---")
    lines.append("系统邮件请勿回复。")

    content = "\n".join(lines)
    print(f"\n📧 检测到房源变化，发送邮件...")
    success = emailSendContent(content, title="浦东公租房 房源变化提醒")
    if success:
        print("✅ 邮件发送成功")
    else:
        print("❌ 邮件发送失败")


def main():
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 检查浦东公租房: {TOWN} + {ROOM_TYPE_NAME}")

    # 0. 加载旧数据
    old_data = load_old_results()

    # 1. 查找航头镇的项目
    project = find_town_project_id(TOWN)
    if not project:
        print(f"[INFO] 未找到 {TOWN} 的项目")
        return

    print(f"[INFO] 找到项目: {project['name']} (ID={project['id']})")
    print(f"[INFO] 项目总房源: {project['houseCount']}, 可租房源: {project['rentableCount']}")

    # 2. 查询两室房源
    total, items = check_house_count(project["id"], ROOM_TYPE)
    print(f"[INFO] {TOWN} + {ROOM_TYPE_NAME}: 可租房源数 = {total}")

    # 3. 构建结果数据
    houses = []
    for item in items:
        houses.append({
            "fullName": item.get("fullName", ""),
            "rentalArea": item.get("rentalArea", ""),
            "floorName": item.get("floorName", ""),
            "toward": item.get("toward", ""),
        })

    output_data = {
        "queryTime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "town": TOWN,
        "roomType": ROOM_TYPE_NAME,
        "project": {
            "id": project["id"],
            "name": project["name"],
            "houseCount": project["houseCount"],
            "rentableCount": project["rentableCount"],
        },
        "targetCount": total,
        "houses": houses,
    }

    # 4. 写入 house.json
    with open(get_output_path(), "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    print(f"✅ 结果已写入: {get_output_path()}")

    # 5. 打印房源详情
    if total > 0:
        msg = (
            f"🎉 有好房源！{TOWN} 现有 {ROOM_TYPE_NAME} 户型可租！\n"
            f"   项目: {project['name']}\n"
            f"   可租数量: {total} 套\n"
            f"   详情: {BASE_URL}/houseLists\n"
            f"   时间: {time.strftime('%Y-%m-%d %H:%M:%S')}"
        )
        send_notification(msg)

        print(f"\n📋 房源详情:")
        for item in houses:
            print(f"   - {item['fullName']}")
            print(f"     面积: {item['rentalArea']}m²  "
                  f"楼层: {item['floorName']}  "
                  f"朝向: {item['toward']}")
    else:
        print(f"😔 {TOWN} 目前没有 {ROOM_TYPE_NAME} 房源可租。")
        print(f"   可租房源总数: {project['rentableCount']} 套（非两室户型）")

    # 6. 对比变化并发送邮件
    if old_data is not None:
        compare_and_notify(old_data, output_data)
    else:
        print("📝 首次运行，已保存 house.json，无历史数据可对比")

    return total


if __name__ == "__main__":
    count = main()
    sys.exit(0 if count > 0 else 1)
