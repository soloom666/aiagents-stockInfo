"""
定时任务页面
管理：主力选股、智策分析、龙虎榜分析、寻龙记 定时任务
"""

import streamlit as st
from datetime import datetime
from scheduled_tasks_manager import (
    get_manager,
    TASK_DEFINITIONS,
    get_run_history,
    CUSTOM_TASK_FUNCTIONS,
    TASK_FUNCTION_DEFINITIONS,
)
from long_term_investment_service import DATA_SOURCE_ALL


EXECUTION_DAY_OPTIONS = {
    "daily": "每天",
    "workday": "工作日（星期一到五）",
    "tomorrow": "明天",
}


def display_scheduled_tasks():
    """定时任务主界面"""

    st.markdown("""
    <div class="top-nav">
        <h1 class="nav-title">⏰ 定时任务管理</h1>
        <p class="nav-subtitle">Scheduled Tasks | 工作日自动执行 · 主力选股 · 智策分析 · 龙虎榜 · 寻龙记</p>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("---")

    manager = get_manager()

    # ── 顶部状态栏 ──────────────────────────────────────────────
    col_status, col_refresh = st.columns([4, 1])
    with col_status:
        if manager.running:
            st.success("🟢 调度服务运行中 — 后台线程每30秒检查一次定时任务")
        else:
            st.warning("🔴 调度服务未运行")

    with col_refresh:
        if st.button("🔄 刷新状态", use_container_width=True):
            st.rerun()

    st.markdown("---")

    # ── 说明 ────────────────────────────────────────────────────
    with st.expander("💡 使用说明", expanded=False):
        st.markdown("""
        **定时自动执行**：启用后，系统每天在设定时间检查任务；部分任务为每天执行，部分任务仅工作日执行。

        | 任务 | 说明 |
        |------|------|
        | 💰 主力选股 | 获取主力资金净流入前100名股票并AI分析，当前默认每天 08:00 |
        | 🎯 智策分析 | AI板块策略综合分析，建议设置早盘（09:15） |
        | 🐉 龙虎榜分析 | 智瞰龙虎分析，当前默认每天 08:00 |
        | 🔮 寻龙记 | 运行 `ai_analysis_run.py`（`AiAnalysis.xunlong`）+ **自动发送邮件至 17521672466@163.com**，当前默认每天 08:30 |
        | 📢 中化公告检查 | 检查中化供应链平台保安/安保公告，变化时邮件通知，默认每天 08:00 |
        | 🏠 浦东公租房检查 | 检查浦东公租房航头镇两室房源，变化时邮件通知，默认每天 08:00 |

        - 点击 **立即执行** 可以不等定时直接触发（在后台线程运行，不阻塞页面）
        - 修改时间后点击 **保存** 立即生效，无需重启
        """)

    st.markdown("---")
    st.subheader("📋 固定任务配置")

    cfg = manager.get_config()
    history = get_run_history()

    # ── 四个任务卡片 ─────────────────────────────────────────────
    for task_id, meta in TASK_DEFINITIONS.items():
        task_cfg = cfg.get(task_id, {})
        task_hist = history.get(task_id, {})

        enabled = task_cfg.get("enabled", False)
        run_time = task_cfg.get("time", meta["default_time"])
        schedule_type = task_cfg.get("schedule_type", meta.get("schedule_type", "daily"))
        last_run = task_hist.get("last_run")
        last_success = task_hist.get("last_success")
        last_msg = task_hist.get("last_msg", "")

        # 卡片容器
        with st.container(border=True):
            header_col, status_col = st.columns([3, 1])
            with header_col:
                st.markdown(f"### {meta['icon']} {meta['name']}")
                st.caption(meta["description"])
            with status_col:
                if last_run:
                    icon = "✅" if last_success else "❌"
                    st.markdown(f"**上次执行**")
                    st.caption(f"{icon} {last_run}")
                    if last_msg:
                        st.caption(last_msg)
                else:
                    st.caption("尚未执行过")

            col_enable, col_day, col_time, col_save, col_run = st.columns([2, 2, 2, 1, 1])

            with col_enable:
                new_enabled = st.toggle(
                    "启用定时",
                    value=enabled,
                    key=f"toggle_{task_id}",
                )

            with col_day:
                new_schedule_type = st.selectbox(
                    "执行日",
                    options=["daily", "workday"],
                    index=["daily", "workday"].index(schedule_type) if schedule_type in ["daily", "workday"] else 0,
                    format_func=lambda key: EXECUTION_DAY_OPTIONS.get(key, key),
                    key=f"schedule_type_{task_id}",
                )

            with col_time:
                # 时间选择：小时 + 分钟
                h_default = int(run_time.split(":")[0])
                m_default = int(run_time.split(":")[1])
                col_h, col_m = st.columns(2)
                with col_h:
                    new_hour = st.number_input(
                        "时",
                        min_value=0, max_value=23,
                        value=h_default,
                        key=f"hour_{task_id}",
                        label_visibility="visible",
                    )
                with col_m:
                    new_min = st.number_input(
                        "分",
                        min_value=0, max_value=59,
                        value=m_default,
                        key=f"min_{task_id}",
                        label_visibility="visible",
                    )
                new_time = f"{int(new_hour):02d}:{int(new_min):02d}"

            with col_save:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("💾 保存", key=f"save_{task_id}", use_container_width=True):
                    manager.update_task(task_id, new_enabled, new_time, new_schedule_type)
                    st.success(
                        f"已保存：{'启用' if new_enabled else '禁用'} · "
                        f"{EXECUTION_DAY_OPTIONS.get(new_schedule_type, new_schedule_type)} · {new_time}"
                    )
                    st.rerun()

            with col_run:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("▶ 立即执行", key=f"run_{task_id}", use_container_width=True):
                    manager.run_now(task_id)
                    st.info(f"✅ {meta['name']} 已在后台启动，请稍后刷新查看结果")

        st.markdown("")  # 间距

    st.markdown("---")
    st.subheader("➕ 新增定时任务")

    with st.container(border=True):
        task_function = st.selectbox(
            "运行功能选择",
            options=list(CUSTOM_TASK_FUNCTIONS.keys()),
            format_func=lambda key: CUSTOM_TASK_FUNCTIONS.get(key, key),
        )
        task_meta = TASK_FUNCTION_DEFINITIONS.get(task_function, {})
        default_task_name = f"{CUSTOM_TASK_FUNCTIONS.get(task_function, task_function)}任务"
        task_name = st.text_input("任务名称", value=default_task_name)
        allowed_sources = task_meta.get("data_sources") or [DATA_SOURCE_ALL]
        supports_data_source = task_meta.get("supports_data_source", False)
        if supports_data_source:
            data_source = st.selectbox("数据源选择", options=allowed_sources)
        else:
            data_source = allowed_sources[0]
            st.text_input("数据源选择", value=data_source, disabled=True)
        enabled = st.toggle("启用任务", value=True, key="new_custom_enabled")
        schedule_type = st.selectbox(
            "执行日",
            options=list(EXECUTION_DAY_OPTIONS.keys()),
            index=1,
            format_func=lambda key: EXECUTION_DAY_OPTIONS.get(key, key),
        )
        col_h, col_m = st.columns(2)
        with col_h:
            custom_hour = st.number_input("执行时", min_value=0, max_value=23, value=15, key="new_custom_hour")
        with col_m:
            custom_min = st.number_input("执行分", min_value=0, max_value=59, value=0, key="new_custom_min")
        custom_time = f"{int(custom_hour):02d}:{int(custom_min):02d}"
        email_receiver = st.text_input(
            "邮件通知收件人（可选，多人用逗号分隔）",
            placeholder="例如: a@163.com, b@163.com",
            key="new_custom_email",
        )
        if st.button("💾 保存新增任务", use_container_width=True):
            manager.save_custom_task(
                {
                    "name": task_name,
                    "function": task_function,
                    "data_source": data_source,
                    "time": custom_time,
                    "enabled": enabled,
                    "schedule_type": schedule_type,
                    "email_receiver": email_receiver.strip(),
                }
            )
            st.success(
                f"已新增任务：{task_name} · {EXECUTION_DAY_OPTIONS.get(schedule_type, schedule_type)} · "
                f"{custom_time} · {data_source}"
            )
            st.rerun()

    custom_tasks = manager.get_custom_tasks()
    if custom_tasks:
        st.markdown("---")
        st.subheader("🧩 自定义任务实例")
        for task in custom_tasks:
            task_id = task.get("task_id")
            hist = history.get(task_id, {})
            with st.container(border=True):
                col_info, col_ops = st.columns([3, 2])
                with col_info:
                    st.markdown(f"### 🧩 {task.get('name', task_id)}")
                    task_meta = TASK_FUNCTION_DEFINITIONS.get(task.get("function"), {})
                    data_source_desc = task.get("data_source") if task_meta.get("supports_data_source") else "无需设置"
                    email_info = f" | 邮件：{task.get('email_receiver')}" if task.get("email_receiver") else ""
                    st.caption(
                        f"功能：{CUSTOM_TASK_FUNCTIONS.get(task.get('function'), task.get('function'))} | "
                        f"执行日：{EXECUTION_DAY_OPTIONS.get(task.get('schedule_type', 'daily'), '每天')} | "
                        f"时间：{task.get('time')} | 数据源：{data_source_desc} | "
                        f"{'启用' if task.get('enabled') else '禁用'}"
                        f"{email_info}"
                    )
                    if hist.get("last_run"):
                        st.caption(
                            f"上次执行：{'✅' if hist.get('last_success') else '❌'} "
                            f"{hist.get('last_run')} {hist.get('last_msg', '')}"
                        )
                with col_ops:
                    if st.button("▶ 立即执行", key=f"run_custom_{task_id}", use_container_width=True):
                        manager.run_now(task_id)
                        st.info("任务已在后台启动")
                    if st.button("🗑️ 删除", key=f"delete_custom_{task_id}", use_container_width=True):
                        manager.delete_custom_task(task_id)
                        st.success("已删除自定义任务")
                        st.rerun()

                with st.expander("✏️ 修改任务", expanded=False):
                    edit_task_meta = TASK_FUNCTION_DEFINITIONS.get(task.get("function"), {})
                    edit_allowed_sources = edit_task_meta.get("data_sources") or [DATA_SOURCE_ALL]
                    edit_supports_data_source = edit_task_meta.get("supports_data_source", False)
                    edit_schedule_type = task.get("schedule_type", "daily")
                    edit_hour_default, edit_min_default = 15, 0
                    if task.get("time") and ":" in str(task.get("time")):
                        edit_hour_default = int(str(task.get("time")).split(":")[0])
                        edit_min_default = int(str(task.get("time")).split(":")[1])

                    with st.form(key=f"edit_custom_form_{task_id}"):
                        edit_name = st.text_input("任务名称", value=task.get("name", ""))
                        edit_enabled = st.toggle("启用任务", value=task.get("enabled", True), key=f"edit_enabled_{task_id}")
                        edit_day = st.selectbox(
                            "执行日",
                            options=list(EXECUTION_DAY_OPTIONS.keys()),
                            index=list(EXECUTION_DAY_OPTIONS.keys()).index(edit_schedule_type)
                            if edit_schedule_type in EXECUTION_DAY_OPTIONS else 0,
                            format_func=lambda key: EXECUTION_DAY_OPTIONS.get(key, key),
                            key=f"edit_day_{task_id}",
                        )
                        edit_col_h, edit_col_m = st.columns(2)
                        with edit_col_h:
                            edit_hour = st.number_input(
                                "执行时",
                                min_value=0,
                                max_value=23,
                                value=edit_hour_default,
                                key=f"edit_hour_{task_id}",
                            )
                        with edit_col_m:
                            edit_min = st.number_input(
                                "执行分",
                                min_value=0,
                                max_value=59,
                                value=edit_min_default,
                                key=f"edit_min_{task_id}",
                            )
                        if edit_supports_data_source:
                            edit_data_source = st.selectbox(
                                "数据源选择",
                                options=edit_allowed_sources,
                                index=edit_allowed_sources.index(task.get("data_source"))
                                if task.get("data_source") in edit_allowed_sources else 0,
                                key=f"edit_data_source_{task_id}",
                            )
                        else:
                            edit_data_source = edit_allowed_sources[0]
                            st.text_input("数据源选择", value=edit_data_source, disabled=True, key=f"edit_data_source_disabled_{task_id}")

                        edit_email_receiver = st.text_input(
                            "邮件通知收件人（可选，多人用逗号分隔）",
                            value=task.get("email_receiver", ""),
                            placeholder="例如: a@163.com, b@163.com",
                            key=f"edit_email_{task_id}",
                        )

                        if st.form_submit_button("💾 保存修改", use_container_width=True):
                            manager.save_custom_task(
                                {
                                    "task_id": task_id,
                                    "name": edit_name,
                                    "function": task.get("function"),
                                    "data_source": edit_data_source,
                                    "time": f"{int(edit_hour):02d}:{int(edit_min):02d}",
                                    "enabled": edit_enabled,
                                    "schedule_type": edit_day,
                                    "email_receiver": edit_email_receiver.strip(),
                                }
                            )
                            st.success("已保存自定义任务修改")
                            st.rerun()

    # ── 当前调度状态 ─────────────────────────────────────────────
    st.markdown("---")
    st.subheader("📅 当前调度计划")

    enabled_tasks = [
        (task_id, cfg[task_id]["time"])
        for task_id in TASK_DEFINITIONS
        if cfg.get(task_id, {}).get("enabled")
    ]

    if enabled_tasks:
        rows = []
        for task_id, t in sorted(enabled_tasks, key=lambda x: x[1]):
            meta = TASK_DEFINITIONS[task_id]
            hist = history.get(task_id, {})
            rows.append({
                "任务": f"{meta['icon']} {meta['name']}",
                "执行时间": t,
                "执行日": EXECUTION_DAY_OPTIONS.get(cfg.get(task_id, {}).get("schedule_type", meta.get("schedule_type", "daily")), "每天"),
                "上次执行": hist.get("last_run", "—"),
                "上次结果": ("✅ 成功" if hist.get("last_success") else "❌ 失败")
                             if hist.get("last_run") else "—",
            })
        import pandas as pd
        custom_rows = []
        for task in sorted(custom_tasks, key=lambda item: item.get("time", "99:99")):
            if not task.get("enabled"):
                continue
            hist = history.get(task.get("task_id"), {})
            custom_rows.append({
                "任务": f"🧩 {task.get('name')}",
                "执行时间": task.get("time"),
                "执行日": EXECUTION_DAY_OPTIONS.get(task.get("schedule_type", "daily"), "每天"),
                "上次执行": hist.get("last_run", "—"),
                "上次结果": ("✅ 成功" if hist.get("last_success") else "❌ 失败") if hist.get("last_run") else "—",
            })
        combined = pd.DataFrame(rows + custom_rows)
        st.dataframe(combined, use_container_width=True, hide_index=True)
    else:
        if any(task.get("enabled") for task in custom_tasks):
            import pandas as pd
            custom_rows = []
            for task in sorted(custom_tasks, key=lambda item: item.get("time", "99:99")):
                if not task.get("enabled"):
                    continue
                hist = history.get(task.get("task_id"), {})
                custom_rows.append({
                    "任务": f"🧩 {task.get('name')}",
                    "执行时间": task.get("time"),
                    "执行日": EXECUTION_DAY_OPTIONS.get(task.get("schedule_type", "daily"), "每天"),
                    "上次执行": hist.get("last_run", "—"),
                    "上次结果": ("✅ 成功" if hist.get("last_success") else "❌ 失败") if hist.get("last_run") else "—",
                })
            st.dataframe(pd.DataFrame(custom_rows), use_container_width=True, hide_index=True)
        else:
            st.info("当前没有启用的定时任务。请在上方开启并保存。")

    # ── 邮件说明 ─────────────────────────────────────────────────
    st.markdown("---")
    with st.expander("📧 邮件通知配置", expanded=False):
        st.markdown("""
        **寻龙记** 任务执行后自动发送 HTML 格式邮件至：

        📮 `17521672466@163.com`

        邮件内容包含：
        - 📈 MACD 策略推荐股票
        - 🔥 妖股策略推荐股票
        - 🎯 AI 龙虎榜推荐股票
        - 🤖 AI Agent 资金/行业/基本面推荐
        - 🆕 本次新增变化股票

        > 邮件发送配置在 `config/emailConfig.yaml` 的 `oStMailCofig` 节点
        """)
