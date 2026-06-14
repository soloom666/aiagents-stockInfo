"""
定时任务管理器
统一管理：固定任务 + 自定义任务实例
"""

import schedule
import subprocess
import sys
import threading
import time
import json
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from long_term_investment_service import DATA_SOURCE_ALL, DATA_SOURCE_MY, LongTermInvestmentService
from xunlong_self_healing_service import XunlongSelfHealingService

# 配置持久化文件
_CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scheduled_tasks_config.json")

TASK_FUNCTION_DEFINITIONS = {
    "main_force": {
        "label": "主力选股",
        "supports_data_source": False,
        "data_sources": [DATA_SOURCE_ALL],
    },
    "sector_strategy": {
        "label": "智策分析",
        "supports_data_source": False,
        "data_sources": [DATA_SOURCE_ALL],
    },
    "longhubang": {
        "label": "龙虎榜分析",
        "supports_data_source": False,
        "data_sources": [DATA_SOURCE_ALL],
    },
    "xunlong": {
        "label": "寻龙记",
        "supports_data_source": True,
        "data_sources": [DATA_SOURCE_ALL, DATA_SOURCE_MY],
    },
    "long_term_investment": {
        "label": "长线投资",
        "supports_data_source": True,
        "data_sources": [DATA_SOURCE_ALL, DATA_SOURCE_MY],
    },
    "xunlong_review": {
        "label": "寻龙记复测",
        "supports_data_source": False,
        "data_sources": [DATA_SOURCE_ALL],
    },
    "portfolio_analysis": {
        "label": "持仓分析",
        "supports_data_source": False,
        "data_sources": [DATA_SOURCE_ALL],
    },
    "monitor_start": {
        "label": "实时监测-启动",
        "supports_data_source": False,
        "data_sources": [DATA_SOURCE_ALL],
    },
    "monitor_stop": {
        "label": "实时监测-停止",
        "supports_data_source": False,
        "data_sources": [DATA_SOURCE_ALL],
    },
    "check_notice": {
        "label": "中化公告检查",
        "supports_data_source": False,
        "data_sources": [DATA_SOURCE_ALL],
    },
    "check_house": {
        "label": "公租房检查",
        "supports_data_source": False,
        "data_sources": [DATA_SOURCE_ALL],
    },
}

CUSTOM_TASK_FUNCTIONS = {key: meta["label"] for key, meta in TASK_FUNCTION_DEFINITIONS.items()}

# 任务定义（元数据）
TASK_DEFINITIONS = {
    "main_force": {
        "name": "主力选股",
        "icon": "💰",
        "description": "获取主力资金净流入前100名股票并进行AI分析",
        "default_time": "08:00",
        "schedule_type": "daily",
        "tag": "scheduled_main_force",
    },
    "sector_strategy": {
        "name": "智策分析",
        "icon": "🎯",
        "description": "AI板块策略综合分析",
        "default_time": "09:15",
        "schedule_type": "workday",
        "tag": "scheduled_sector_strategy",
    },
    "longhubang": {
        "name": "龙虎榜分析",
        "icon": "🐉",
        "description": "龙虎榜多智能体综合分析",
        "default_time": "08:00",
        "schedule_type": "daily",
        "tag": "scheduled_longhubang",
    },
    "xunlong": {
        "name": "寻龙记",
        "icon": "🔮",
        "description": "运行 ai_analysis_run.py（AiAnalysis.xunlong）并发送邮件通知",
        "default_time": "08:30",
        "schedule_type": "daily",
        "tag": "scheduled_xunlong",
    },
    "check_notice": {
        "name": "中化公告检查",
        "icon": "📢",
        "description": "检查中化供应链平台保安/安保公告，变化时邮件通知",
        "default_time": "08:00",
        "schedule_type": "daily",
        "tag": "scheduled_check_notice",
    },
    "check_house": {
        "name": "浦东公租房检查",
        "icon": "🏠",
        "description": "检查浦东公租房平台航头镇两室房源，变化时邮件通知",
        "default_time": "08:00",
        "schedule_type": "daily",
        "tag": "scheduled_check_house",
    },
}


def _default_config() -> Dict[str, Any]:
    cfg = {
        task_id: {
            "enabled": False,
            "time": meta["default_time"],
            "schedule_type": meta["schedule_type"],
        }
        for task_id, meta in TASK_DEFINITIONS.items()
    }
    cfg["custom_tasks"] = []
    return cfg


def _load_config() -> Dict[str, Any]:
    try:
        if os.path.exists(_CONFIG_FILE):
            with open(_CONFIG_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
            cfg = _default_config()
            for tid in TASK_DEFINITIONS:
                if tid in saved:
                    cfg[tid].update(saved[tid])
            cfg["custom_tasks"] = saved.get("custom_tasks", [])
            return cfg
    except Exception as e:
        print(f"[定时任务] 配置加载失败: {e}")
    return _default_config()


def _save_config(cfg: Dict[str, Any]):
    try:
        with open(_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[定时任务] 配置保存失败: {e}")


# ── 任务执行函数 ────────────────────────────────────────────────

def _is_workday() -> bool:
    """判断今天是否工作日（周一到周五）"""
    return datetime.now().weekday() < 5


def _should_run_today(task_id: str) -> bool:
    """按任务调度类型判断今天是否应执行。"""
    task_cfg = get_manager().get_config().get(task_id, {})
    schedule_type = task_cfg.get("schedule_type") or TASK_DEFINITIONS[task_id].get("schedule_type", "workday")
    if schedule_type == "daily":
        return True
    return _is_workday()


def _should_run_custom_task_today(task: Dict[str, Any]) -> bool:
    """按自定义任务执行日判断今天是否应执行。"""
    schedule_type = task.get("schedule_type", "daily")
    if schedule_type == "daily":
        return True
    if schedule_type == "workday":
        return _is_workday()
    if schedule_type == "tomorrow":
        run_date = task.get("run_date")
        return run_date == datetime.now().strftime("%Y-%m-%d")
    return True


def _run_main_force():
    """执行主力选股"""
    if not _should_run_today("main_force"):
        print("[定时任务] 非执行日，跳过主力选股")
        return
    print(f"\n[定时任务] 🚀 主力选股 开始 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    try:
        from main_force_analysis import main_force_analyzer
        result = main_force_analyzer.run_full_analysis(
            days_ago=30,
            final_n=5,
            max_range_change=30,
            min_market_cap=20,
            max_market_cap=500,
        )
        status = "✓ 成功" if result.get("success") else f"✗ 失败: {result.get('error','')}"
        print(f"[定时任务] 主力选股 {status}")
        _update_last_run("main_force", result.get("success", False),
                         f"筛选到 {result.get('filtered_stocks', 0)} 只，精选 {len(result.get('final_recommendations', []))} 只")
    except Exception as e:
        print(f"[定时任务] ✗ 主力选股 异常: {e}")
        _update_last_run("main_force", False, str(e))


def _run_sector_strategy():
    """执行智策分析"""
    if not _should_run_today("sector_strategy"):
        print("[定时任务] 非执行日，跳过智策分析")
        return
    print(f"\n[定时任务] 🚀 智策分析 开始 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    try:
        from sector_strategy_data import SectorStrategyDataFetcher
        from sector_strategy_engine import SectorStrategyEngine
        fetcher = SectorStrategyDataFetcher()
        data = fetcher.get_all_sector_data()
        if not data.get("success"):
            _update_last_run("sector_strategy", False, "数据获取失败")
            return
        engine = SectorStrategyEngine(model="deepseek-chat")
        result = engine.run_comprehensive_analysis(data)
        status = "✓ 成功" if result.get("success") else f"✗ 失败"
        print(f"[定时任务] 智策分析 {status}")
        _update_last_run("sector_strategy", result.get("success", False), "分析完成")
    except Exception as e:
        print(f"[定时任务] ✗ 智策分析 异常: {e}")
        _update_last_run("sector_strategy", False, str(e))


def _run_longhubang():
    """执行龙虎榜分析"""
    if not _should_run_today("longhubang"):
        print("[定时任务] 非执行日，跳过龙虎榜分析")
        return
    print(f"\n[定时任务] 🚀 龙虎榜分析 开始 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    try:
        from longhubang_engine import LonghubangEngine
        engine = LonghubangEngine()
        result = engine.run_comprehensive_analysis(days=1)
        status = "✓ 成功" if result.get("success") else f"✗ 失败"
        print(f"[定时任务] 龙虎榜分析 {status}")
        rec_count = len(result.get("recommended_stocks", []))
        _update_last_run("longhubang", result.get("success", False),
                         f"推荐 {rec_count} 只股票")
    except Exception as e:
        print(f"[定时任务] ✗ 龙虎榜分析 异常: {e}")
        _update_last_run("longhubang", False, str(e))


def _run_xunlong():
    """执行寻龙记并发送邮件"""
    if not _should_run_today("xunlong"):
        print("[定时任务] 非执行日，跳过寻龙记")
        return
    print(f"\n[定时任务] 🚀 寻龙记 开始 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    try:
        from aitrader.a_self_Strategy.ai_analysis.ai_analysis_run import AiAnalysis
        result = AiAnalysis.xunlong(data_source=DATA_SOURCE_MY, fast_mode=True)
        if result:
            _send_xunlong_email(result)
            macd_n = len(result.get("macd") or [])
            yaogu_n = len(result.get("yaogu") or [])
            _update_last_run("xunlong", True, f"MACD {macd_n} 只，妖股 {yaogu_n} 只，已发送邮件")
        else:
            _update_last_run("xunlong", False, "无返回数据")
    except ImportError as e:
        missing_module = getattr(e, "name", None) or str(e)
        msg = (
            "寻龙记依赖未安装或未安装完整。"
            f" 当前缺少模块: `{missing_module}`。"
            " 请先执行 `python -m pip install -r requirements-quant.txt`，"
            "并优先使用 Python 3.12 环境"
        )
        print(f"[定时任务] ✗ 寻龙记 异常: {msg} ({e})")
        _update_last_run("xunlong", False, msg)
    except Exception as e:
        print(f"[定时任务] ✗ 寻龙记 异常: {e}")
        _update_last_run("xunlong", False, str(e))


def _run_long_term_investment(data_source: str = DATA_SOURCE_ALL):
    print(f"\n[定时任务] 🚀 长线投资 开始 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 数据源={data_source}")
    try:
        service = LongTermInvestmentService()
        result = service.screen(data_source=data_source)
        count = len(result.get("rows", []))
        print(f"[定时任务] 长线投资 ✓ 成功，筛选 {count} 只")
        return result
    except Exception as exc:
        print(f"[定时任务] ✗ 长线投资 异常: {exc}")
        raise


def _run_xunlong_review():
    print(f"\n[定时任务] 🚀 寻龙记复测 开始 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    try:
        service = XunlongSelfHealingService()
        result = service.review_due_feedback()
        print(f"[定时任务] 寻龙记复测 ✓ {result.get('message', '完成')}")
        return result
    except Exception as exc:
        print(f"[定时任务] ✗ 寻龙记复测 异常: {exc}")
        raise


def _run_portfolio_analysis():
    print(f"\n[定时任务] 🚀 持仓分析 开始 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    try:
        from portfolio_scheduler import portfolio_scheduler

        ok = portfolio_scheduler.run_analysis_now()
        print(f"[定时任务] 持仓分析 {'✓ 成功' if ok else '✗ 失败'}")
        return {"success": bool(ok), "message": "持仓分析完成" if ok else "持仓分析失败"}
    except Exception as exc:
        print(f"[定时任务] ✗ 持仓分析 异常: {exc}")
        raise


def _run_monitor_start():
    print(f"\n[定时任务] 🚀 实时监测启动 开始 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    try:
        from monitor_service import monitor_service

        monitor_service.start_monitoring()
        print("[定时任务] 实时监测 ✓ 已启动")
        return {"success": True, "message": "实时监测已启动"}
    except Exception as exc:
        print(f"[定时任务] ✗ 实时监测启动异常: {exc}")
        raise


def _run_monitor_stop():
    print(f"\n[定时任务] 🚀 实时监测停止 开始 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    try:
        from monitor_service import monitor_service

        monitor_service.stop_monitoring()
        print("[定时任务] 实时监测 ✓ 已停止")
        return {"success": True, "message": "实时监测已停止"}
    except Exception as exc:
        print(f"[定时任务] ✗ 实时监测停止异常: {exc}")
        raise


def _run_check_notice():
    """执行中化公告检查"""
    print(f"\n[定时任务] 🚀 中化公告检查 开始 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    try:
        script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "common", "get_info", "check_notice.py")
        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120,
            cwd=os.path.dirname(os.path.abspath(__file__)),
        )
        output = (result.stdout or "").strip()
        if output:
            for line in output.splitlines():
                print(f"[定时任务]   {line}")
        if result.returncode != 0:
            stderr = (result.stderr or "").strip()
            if stderr:
                print(f"[定时任务]   stderr: {stderr[:500]}")
        status = "✓ 完成" if result.returncode == 0 else f"✗ 退出码 {result.returncode}"
        print(f"[定时任务] 中化公告检查 {status}")
        _update_last_run("check_notice", result.returncode == 0, status)
    except subprocess.TimeoutExpired:
        print("[定时任务] ✗ 中化公告检查 超时")
        _update_last_run("check_notice", False, "执行超时")
    except Exception as e:
        print(f"[定时任务] ✗ 中化公告检查 异常: {e}")
        _update_last_run("check_notice", False, str(e))


def _run_check_house():
    """执行公租房检查"""
    print(f"\n[定时任务] 🚀 浦东公租房检查 开始 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    try:
        script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "common", "get_info", "check_house.py")
        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120,
            cwd=os.path.dirname(os.path.abspath(__file__)),
        )
        output = (result.stdout or "").strip()
        if output:
            for line in output.splitlines():
                print(f"[定时任务]   {line}")
        if result.returncode != 0:
            stderr = (result.stderr or "").strip()
            if stderr:
                print(f"[定时任务]   stderr: {stderr[:500]}")
        status = "✓ 完成" if result.returncode == 0 else f"✗ 退出码 {result.returncode}"
        print(f"[定时任务] 浦东公租房检查 {status}")
        _update_last_run("check_house", result.returncode == 0, status)
    except subprocess.TimeoutExpired:
        print("[定时任务] ✗ 浦东公租房检查 超时")
        _update_last_run("check_house", False, "执行超时")
    except Exception as e:
        print(f"[定时任务] ✗ 浦东公租房检查 异常: {e}")
        _update_last_run("check_house", False, str(e))


def _send_xunlong_email(result: Dict, email_receiver=None):
    """通过通用 send_task_email 发送寻龙记 HTML 邮件"""
    from aitrader.common.emailSendFiles import send_task_email

    macd_stocks = result.get("macd") or []
    yaogu_stocks = result.get("yaogu") or []
    diff_stocks = result.get("diff") or []
    al_agent = result.get("al_agent_stocks") or {}

    def _fmt_list(lst):
        if not lst:
            return "无"
        if isinstance(lst, list):
            return "、".join(str(x) for x in lst)
        return str(lst)

    main_stocks = al_agent.get("main_stocks", {}) if al_agent else {}
    agent_lines = ""
    if main_stocks:
        agent_lines = f"""
<tr><td style="padding:8px;color:#888;">资金流向推荐</td><td style="padding:8px;">{_fmt_list(main_stocks.get('fund_flow_analysis_codes'))}</td></tr>
<tr><td style="padding:8px;color:#888;">行业分析推荐</td><td style="padding:8px;">{_fmt_list(main_stocks.get('industry_analysis_codes'))}</td></tr>
<tr><td style="padding:8px;color:#888;">基本面推荐</td><td style="padding:8px;">{_fmt_list(main_stocks.get('fundamental_analysis_codes'))}</td></tr>
"""
    lhb_stocks = _fmt_list(al_agent.get("longhuban_stocks")) if al_agent else "无"

    report_date = datetime.now().strftime("%Y-%m-%d")
    title = f"🔮 寻龙记选股报告 {report_date}"

    # 纯文本正文（邮件客户端不支持 HTML 时的回退）
    plain_text = f"""寻龙记 · 今日选股报告

报告时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

MACD策略：{_fmt_list(macd_stocks)}
妖股策略：{_fmt_list(yaogu_stocks)}
AI龙虎榜：{lhb_stocks}
新增变化：{_fmt_list(diff_stocks)}

系统自动发送，请勿回复。
"""

    # HTML 正文
    body_html = f"""
<html><body style="font-family:Arial,sans-serif;background:#f5f5f5;padding:20px;">
<div style="background:white;border-radius:10px;padding:24px;max-width:600px;margin:0 auto;
            box-shadow:0 2px 8px rgba(0,0,0,0.1);">
  <h2 style="color:#1a3a5c;border-bottom:2px solid #4fc3f7;padding-bottom:10px;">
    🔮 寻龙记 · 今日选股报告
  </h2>
  <p style="color:#666;">报告时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
  <table style="width:100%;border-collapse:collapse;margin-top:16px;">
    <tr style="background:#e3f2fd;">
      <td style="padding:8px;font-weight:bold;color:#1a3a5c;">策略</td>
      <td style="padding:8px;font-weight:bold;color:#1a3a5c;">推荐股票</td>
    </tr>
    <tr><td style="padding:8px;color:#888;">📈 MACD策略</td><td style="padding:8px;">{_fmt_list(macd_stocks)}</td></tr>
    <tr style="background:#fafafa;"><td style="padding:8px;color:#888;">🔥 妖股策略</td><td style="padding:8px;">{_fmt_list(yaogu_stocks)}</td></tr>
    <tr><td style="padding:8px;color:#888;">🎯 AI龙虎榜</td><td style="padding:8px;">{lhb_stocks}</td></tr>
    {agent_lines}
    <tr style="background:#fff3e0;"><td style="padding:8px;color:#e65100;font-weight:bold;">🆕 新增变化</td><td style="padding:8px;font-weight:bold;">{_fmt_list(diff_stocks)}</td></tr>
  </table>
  <p style="color:#aaa;font-size:12px;margin-top:24px;">系统自动发送，请勿回复</p>
</div>
</body></html>
"""

    success = send_task_email("xunlong", plain_text, title=title, body_html=body_html, receiver=email_receiver)
    if success:
        print(f"[定时任务] ✓ 寻龙记邮件已发送")
    else:
        print(f"[定时任务] ✗ 寻龙记邮件发送失败")


# ── 运行历史记录 ─────────────────────────────────────────────────

_run_history: Dict[str, Dict] = {tid: {"last_run": None, "last_success": None, "last_msg": ""} for tid in TASK_DEFINITIONS}
_history_lock = threading.Lock()


def _update_last_run(task_id: str, success: bool, msg: str = ""):
    with _history_lock:
        _run_history[task_id] = {
            "last_run": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "last_success": success,
            "last_msg": msg,
        }


def get_run_history() -> Dict[str, Dict]:
    with _history_lock:
        return dict(_run_history)


# ── 调度器主类 ───────────────────────────────────────────────────

class ScheduledTasksManager:
    """统一定时任务管理器（进程级单例）"""

    _TASK_FNS = {
        "main_force": _run_main_force,
        "sector_strategy": _run_sector_strategy,
        "longhubang": _run_longhubang,
        "xunlong": _run_xunlong,
        "check_notice": _run_check_notice,
        "check_house": _run_check_house,
    }

    def __init__(self):
        self._config: Dict[str, Any] = _load_config()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._task_locks: Dict[str, threading.Lock] = {tid: threading.Lock() for tid in TASK_DEFINITIONS}
        self._custom_task_locks: Dict[str, threading.Lock] = {}
        print("[定时任务] 管理器初始化完成")

    # ── 配置 ─────────────────────────────────────────────────────

    def get_config(self) -> Dict[str, Any]:
        return dict(self._config)

    def get_custom_tasks(self) -> List[Dict[str, Any]]:
        return list(self._config.get("custom_tasks", []))

    def update_task(self, task_id: str, enabled: bool, run_time: str, schedule_type: Optional[str] = None):
        """更新单个任务配置并重新调度"""
        if task_id not in TASK_DEFINITIONS:
            return
        current = self._config.get(task_id, {})
        self._config[task_id] = {
            "enabled": enabled,
            "time": run_time,
            "schedule_type": schedule_type or current.get("schedule_type") or TASK_DEFINITIONS[task_id]["schedule_type"],
        }
        _save_config(self._config)
        if self._running:
            self._reschedule_task(task_id)
        print(
            f"[定时任务] 更新任务 {task_id}: enabled={enabled}, "
            f"time={run_time}, schedule_type={self._config[task_id]['schedule_type']}"
        )

    def save_custom_task(self, task: Dict[str, Any]):
        custom_tasks = self._config.setdefault("custom_tasks", [])
        task_id = str(task.get("task_id") or f"custom_{int(time.time() * 1000)}")
        task["task_id"] = task_id
        task.setdefault("name", f"{CUSTOM_TASK_FUNCTIONS.get(task.get('function'), '自定义任务')}任务")
        task.setdefault("enabled", True)
        task.setdefault("time", "15:00")
        task["schedule_type"] = task.get("schedule_type") or "daily"
        if task["schedule_type"] == "tomorrow":
            task["run_date"] = task.get("run_date") or (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        else:
            task.pop("run_date", None)
        function_meta = TASK_FUNCTION_DEFINITIONS.get(task.get("function"), {})
        allowed_sources = function_meta.get("data_sources") or [DATA_SOURCE_ALL]
        task["data_source"] = task.get("data_source") if task.get("data_source") in allowed_sources else allowed_sources[0]

        exists = False
        for idx, item in enumerate(custom_tasks):
            if item.get("task_id") == task_id:
                custom_tasks[idx] = task
                exists = True
                break
        if not exists:
            custom_tasks.append(task)

        _save_config(self._config)
        if self._running:
            self._reschedule_custom_task(task_id)
        print(f"[定时任务] 保存自定义任务 {task_id}")

    def delete_custom_task(self, task_id: str):
        custom_tasks = self._config.setdefault("custom_tasks", [])
        self._config["custom_tasks"] = [item for item in custom_tasks if item.get("task_id") != task_id]
        _save_config(self._config)
        if self._running:
            self._clear_custom_task_jobs(task_id)
        print(f"[定时任务] 删除自定义任务 {task_id}")

    # ── 启动 / 停止 ───────────────────────────────────────────────

    def start(self):
        with self._lock:
            if self._running:
                return
            self._running = True
            self._rebuild_schedule()
            self._thread = threading.Thread(target=self._loop, daemon=True, name="ScheduledTasksLoop")
            self._thread.start()
            print("[定时任务] ✓ 后台调度线程已启动")

    def stop(self):
        with self._lock:
            self._running = False
            self._clear_all_schedule_jobs()
            print("[定时任务] ✓ 已停止")

    @property
    def running(self) -> bool:
        return self._running

    # ── 立即执行 ──────────────────────────────────────────────────

    def run_now(self, task_id: str):
        """在新线程中立即执行指定任务"""
        if task_id in TASK_DEFINITIONS:
            self._start_task_thread(task_id, source="manual")
            return
        self._start_custom_task_thread(task_id, source="manual")

    # ── 内部调度 ──────────────────────────────────────────────────

    def _loop(self):
        while self._running:
            try:
                schedule.run_pending()
            except Exception as e:
                print(f"[定时任务] ✗ 调度循环异常: {e}")
            time.sleep(30)

    def _make_safe_job(self, task_id: str):
        def _safe():
            self._start_task_thread(task_id, source="schedule")
        return _safe

    def _start_task_thread(self, task_id: str, source: str = "schedule"):
        """以后台线程启动任务，避免同一时刻多个任务互相阻塞。"""
        fn = self._TASK_FNS.get(task_id)
        if not fn:
            return

        lock = self._task_locks[task_id]

        def _wrapped():
            if not lock.acquire(blocking=False):
                msg = "上次还未完成，跳过" if source == "schedule" else "正在运行中，跳过"
                print(f"[定时任务] ⚠️ {task_id} {msg}")
                return
            try:
                fn()
            finally:
                lock.release()

        thread_name = f"{source.capitalize()}Task_{task_id}"
        threading.Thread(target=_wrapped, daemon=True, name=thread_name).start()

    def _dispatch_custom_task(self, task: Dict[str, Any]):
        function = task.get("function")
        data_source = task.get("data_source", DATA_SOURCE_ALL)
        email_receiver = task.get("email_receiver", "")

        # 将页面配置的邮件收件人注入到环境变量，供子进程脚本读取
        if email_receiver:
            os.environ["TASK_EMAIL_RECEIVER"] = str(email_receiver)
        else:
            os.environ.pop("TASK_EMAIL_RECEIVER", None)

        if function == "main_force":
            return _run_main_force()
        if function == "sector_strategy":
            return _run_sector_strategy()
        if function == "longhubang":
            return _run_longhubang()
        if function == "xunlong":
            from aitrader.a_self_Strategy.ai_analysis.ai_analysis_run import AiAnalysis
            result = AiAnalysis.xunlong(data_source=data_source, fast_mode=True)
            if result:
                _send_xunlong_email(result, email_receiver=email_receiver or None)
            return result
        if function == "long_term_investment":
            return _run_long_term_investment(data_source=data_source)
        if function == "xunlong_review":
            return _run_xunlong_review()
        if function == "portfolio_analysis":
            return _run_portfolio_analysis()
        if function == "monitor_start":
            return _run_monitor_start()
        if function == "monitor_stop":
            return _run_monitor_stop()
        if function == "check_notice":
            return _run_check_notice()
        if function == "check_house":
            return _run_check_house()
        raise ValueError(f"未知任务功能: {function}")

    def _start_custom_task_thread(self, task_id: str, source: str = "schedule"):
        task = next((item for item in self._config.get("custom_tasks", []) if item.get("task_id") == task_id), None)
        if not task:
            return

        lock = self._custom_task_locks.setdefault(task_id, threading.Lock())

        def _wrapped():
            if not lock.acquire(blocking=False):
                print(f"[定时任务] ⚠️ 自定义任务 {task_id} 正在运行中，跳过")
                return
            try:
                if source == "schedule" and not _should_run_custom_task_today(task):
                    print(f"[定时任务] 自定义任务 {task.get('name', task_id)} 非执行日，跳过")
                    return
                result = self._dispatch_custom_task(task)
                _update_last_run(task_id, True, f"执行成功: {task.get('name')}")
                if source == "schedule" and task.get("schedule_type") == "tomorrow":
                    task["enabled"] = False
                    _save_config(self._config)
                    if self._running:
                        self._clear_custom_task_jobs(task_id)
                    print(f"[定时任务] 自定义任务 {task.get('name', task_id)} 已完成，已自动禁用")
                return result
            except Exception as exc:
                _update_last_run(task_id, False, str(exc))
            finally:
                lock.release()

        thread_name = f"{source.capitalize()}CustomTask_{task_id}"
        threading.Thread(target=_wrapped, daemon=True, name=thread_name).start()

    def _clear_task_jobs(self, task_id: str):
        tag = TASK_DEFINITIONS[task_id]["tag"]
        jobs = [j for j in schedule.jobs if tag in j.tags]
        for j in jobs:
            schedule.cancel_job(j)

    def _clear_all_schedule_jobs(self):
        for task_id in TASK_DEFINITIONS:
            self._clear_task_jobs(task_id)
        for task in self._config.get("custom_tasks", []):
            self._clear_custom_task_jobs(task.get("task_id"))

    def _reschedule_task(self, task_id: str):
        self._clear_task_jobs(task_id)
        cfg = self._config.get(task_id, {})
        if cfg.get("enabled"):
            run_time = cfg.get("time", TASK_DEFINITIONS[task_id]["default_time"])
            tag = TASK_DEFINITIONS[task_id]["tag"]
            job = schedule.every().day.at(run_time).do(self._make_safe_job(task_id))
            job.tag(tag)
            print(f"[定时任务] 已调度 {task_id} @ {run_time}")

    def _make_safe_custom_job(self, task_id: str):
        def _safe():
            self._start_custom_task_thread(task_id, source="schedule")
        return _safe

    def _clear_custom_task_jobs(self, task_id: str):
        tag = f"custom_task_{task_id}"
        jobs = [j for j in schedule.jobs if tag in j.tags]
        for job in jobs:
            schedule.cancel_job(job)

    def _reschedule_custom_task(self, task_id: str):
        self._clear_custom_task_jobs(task_id)
        task = next((item for item in self._config.get("custom_tasks", []) if item.get("task_id") == task_id), None)
        if not task or not task.get("enabled"):
            return
        run_time = task.get("time", "15:00")
        tag = f"custom_task_{task_id}"
        job = schedule.every().day.at(run_time).do(self._make_safe_custom_job(task_id))
        job.tag(tag)
        print(f"[定时任务] 已调度自定义任务 {task_id} @ {run_time}")

    def _rebuild_schedule(self):
        self._clear_all_schedule_jobs()
        for task_id in TASK_DEFINITIONS:
            self._reschedule_task(task_id)
        for task in self._config.get("custom_tasks", []):
            self._reschedule_custom_task(task.get("task_id"))


# ── 进程级单例 ────────────────────────────────────────────────────

_manager_instance: Optional[ScheduledTasksManager] = None
_manager_init_lock = threading.Lock()


def get_manager() -> ScheduledTasksManager:
    """获取进程级单例管理器，首次调用时自动启动后台线程"""
    global _manager_instance
    if _manager_instance is None:
        with _manager_init_lock:
            if _manager_instance is None:
                _manager_instance = ScheduledTasksManager()
                _manager_instance.start()
    return _manager_instance
