"""
登录 & 用户管理界面
"""
from __future__ import annotations

import streamlit as st
from auth import (
    login,
    create_user,
    get_all_users,
    set_user_active,
    change_role,
    change_password,
    delete_user,
    update_user_llm_config,
    get_role_label,
    sync_runtime_llm_env,
    clear_runtime_llm_env,
    generate_session_token,
    validate_session_token,
    ROLE_OPTIONS,
)
from model_config import model_options, get_model_label, build_model_options_with_current


# ──────────────────────────────────────────────
# 公共辅助
# ──────────────────────────────────────────────

def is_logged_in() -> bool:
    return st.session_state.get("logged_in", False)


def current_user() -> dict | None:
    return st.session_state.get("auth_user", None)


def is_admin() -> bool:
    user = current_user()
    return user is not None and user.get("role") == "admin"


def is_vip() -> bool:
    user = current_user()
    return user is not None and user.get("role") == "vip"


def can_access_user_management() -> bool:
    return is_admin()


def _reset_user_mgmt_llm_form_fields(prefix: str) -> None:
    """切换到自定义模型时，清空同区域相关输入项。"""
    st.session_state[f"{prefix}_api_key"] = ""
    st.session_state[f"{prefix}_base_url"] = ""
    st.session_state[f"{prefix}_custom_model"] = ""


def logout():
    for key in ("logged_in", "auth_user"):
        if key in st.session_state:
            del st.session_state[key]
    clear_runtime_llm_env()
    st.query_params.pop("_t", None)
    st.rerun()


# ──────────────────────────────────────────────
# 登录页
# ──────────────────────────────────────────────

def check_persistent_login() -> bool:
    """检查 URL query params 中是否有有效 session token，有则自动恢复登录状态"""
    try:
        token = st.query_params.get("_t")
        if not token:
            return False
        user = validate_session_token(token)
        if user:
            st.session_state.logged_in = True
            st.session_state.auth_user = user
            sync_runtime_llm_env(user)
            return True
        else:
            # token 无效或过期，清除
            st.query_params.pop("_t", None)
    except Exception:
        pass
    return False


def show_login_page():
    """展示登录页面，未通过认证时调用"""
    st.markdown("""
    <style>
        .login-wrapper {
            max-width: 420px;
            margin: 6rem auto 0;
            padding: 2.5rem 2rem;
            background: #fff;
            border-radius: 16px;
            box-shadow: 0 8px 32px rgba(102,126,234,0.18);
        }
        .login-title {
            text-align: center;
            font-size: 1.6rem;
            font-weight: 700;
            color: #667eea;
            margin-bottom: 0.3rem;
        }
        .login-sub {
            text-align: center;
            color: #888;
            font-size: 0.9rem;
            margin-bottom: 1.8rem;
        }
    </style>
    """, unsafe_allow_html=True)

    # 居中容器
    _, col, _ = st.columns([1, 2, 1])
    with col:
        # st.markdown('<div class="login-wrapper">', unsafe_allow_html=True)
        st.markdown('<p class="login-title">📈 AI股票分析系统</p>', unsafe_allow_html=True)
        st.markdown('<p class="login-sub">请登录以继续使用</p>', unsafe_allow_html=True)

        with st.form("login_form", clear_on_submit=False):
            username = st.text_input("用户名", placeholder="请输入用户名")
            password = st.text_input("密码", type="password", placeholder="请输入密码")
            submitted = st.form_submit_button("登 录", use_container_width=True, type="primary")

        if submitted:
            if not username or not password:
                st.error("请输入用户名和密码")
            else:
                with st.spinner("验证中..."):
                    user = login(username.strip(), password)
                if user:
                    st.session_state.logged_in = True
                    st.session_state.auth_user = user
                    sync_runtime_llm_env(user)
                    st.query_params["_t"] = generate_session_token(user["id"])
                    st.success(f"欢迎回来，{user['username']}！")
                    st.rerun()
                else:
                    st.error("用户名或密码错误，或账号已被禁用")

        st.markdown('</div>', unsafe_allow_html=True)


# ──────────────────────────────────────────────
# 侧边栏用户信息 & 注销
# ──────────────────────────────────────────────

def show_sidebar_user_info():
    """在侧边栏底部显示当前用户信息和注销按钮"""
    user = current_user()
    if not user:
        return

    st.sidebar.markdown("---")
    role_label = get_role_label(user["role"])
    st.sidebar.markdown(
        f"**👤 {user['username']}** &nbsp; `{role_label}`",
        unsafe_allow_html=True,
    )

    # 管理员入口
    if can_access_user_management():
        if st.sidebar.button("👥 用户管理", key="nav_user_mgmt", use_container_width=True):
            st.session_state.show_user_mgmt = True
            # 清除其他页面标志
            for key in [
                "show_history", "show_monitor", "show_config", "show_main_force",
                "show_sector_strategy", "show_longhubang", "show_portfolio",
                "show_smart_monitor",
            ]:
                st.session_state.pop(key, None)

    if st.sidebar.button("🚪 退出登录", key="logout_btn", use_container_width=True):
        logout()


# ──────────────────────────────────────────────
# 用户管理页（仅管理员）
# ──────────────────────────────────────────────

def show_user_management():
    """管理员用户管理界面"""
    if not can_access_user_management():
        st.error("权限不足，仅管理员可访问此页面")
        return

    st.subheader("👥 用户管理")

    # ── 新建用户 ──
    with st.expander("➕ 新建用户", expanded=False):
        with st.form("create_user_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            new_username = c1.text_input("用户名")
            new_role = c2.selectbox("角色", list(ROLE_OPTIONS), format_func=get_role_label)
            new_password = st.text_input("密码（不少于6位）", type="password")
            if st.form_submit_button("创建", type="primary"):
                ok, msg = create_user(new_username.strip(), new_password, new_role)
                if ok:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)

    st.markdown("---")

    # ── 用户列表 ──
    users = get_all_users()
    current_uid = current_user()["id"]

    if not users:
        st.info("暂无用户")
        return

    # 表头
    h_cols = st.columns([1, 2, 2, 2, 2, 2, 3])
    for col, title in zip(h_cols, ["ID", "用户名", "角色", "状态", "创建时间", "最后登录", "操作"]):
        col.markdown(f"**{title}**")
    st.markdown("---")

    for user in users:
        uid = user["id"]
        cols = st.columns([1, 2, 2, 2, 2, 2, 3])
        cols[0].write(uid)
        cols[1].write(user["username"])
        cols[2].write(get_role_label(user["role"]))
        cols[3].write("✅ 启用" if user["is_active"] else "🔴 禁用")
        cols[4].write(str(user["created_at"])[:10] if user["created_at"] else "-")
        cols[5].write(str(user["last_login"])[:16] if user["last_login"] else "未登录")

        with cols[6]:
            op1, op2, op3 = st.columns(3)

            # 启用/禁用（不能操作自己）
            if uid != current_uid:
                label = "禁用" if user["is_active"] else "启用"
                if op1.button(label, key=f"active_{uid}", use_container_width=True):
                    ok, msg = set_user_active(uid, not user["is_active"])
                    (st.success if ok else st.error)(msg)
                    st.rerun()
            else:
                op1.write("")  # 占位

            # 切换角色（不能操作自己）
            if uid != current_uid:
                role_choices = [role for role in ROLE_OPTIONS if role != user["role"]]
                target_role = op2.selectbox(
                    "目标角色",
                    options=role_choices,
                    format_func=get_role_label,
                    key=f"role_select_{uid}",
                    label_visibility="collapsed"
                )
                if op2.button("修改角色", key=f"role_{uid}", use_container_width=True):
                    ok, msg = change_role(uid, target_role)
                    (st.success if ok else st.error)(msg)
                    st.rerun()
            else:
                op2.write("")

            # 删除（不能删除自己）
            if uid != current_uid:
                if op3.button("删除", key=f"del_{uid}", use_container_width=True):
                    ok, msg = delete_user(uid)
                    (st.success if ok else st.error)(msg)
                    st.rerun()
            else:
                op3.write("")

    # ── 修改密码 ──
    st.markdown("---")
    with st.expander("🔑 重置用户密码", expanded=False):
        with st.form("reset_pw_form", clear_on_submit=True):
            user_options = {u["id"]: u["username"] for u in users}
            target_uid = st.selectbox(
                "选择用户",
                options=list(user_options.keys()),
                format_func=lambda x: user_options[x],
            )
            new_pw = st.text_input("新密码（不少于6位）", type="password")
            if st.form_submit_button("重置密码", type="primary"):
                ok, msg = change_password(target_uid, new_pw)
                (st.success if ok else st.error)(msg)
                if ok:
                    st.rerun()

    st.markdown("---")
    with st.expander("🤖 当前用户大模型配置", expanded=True):
        auth_user = current_user() or {}
        current_api_key = auth_user.get("llm_api_key", "")
        current_base_url = auth_user.get("llm_base_url", "")
        current_model = auth_user.get("llm_model", "deepseek-chat")

        with st.form("user_llm_config_form", clear_on_submit=False):
            model_options_map = build_model_options_with_current(current_model)
            model_keys = list(model_options_map.keys())
            model_type_key = "user_mgmt_llm_model_type"
            api_key_input_key = "user_mgmt_llm_api_key"
            base_url_input_key = "user_mgmt_llm_base_url"
            custom_model_input_key = "user_mgmt_llm_custom_model"

            if model_type_key not in st.session_state:
                st.session_state[model_type_key] = current_model if current_model in model_keys else "__custom__"
            if api_key_input_key not in st.session_state:
                st.session_state[api_key_input_key] = current_api_key
            if base_url_input_key not in st.session_state:
                st.session_state[base_url_input_key] = current_base_url
            if custom_model_input_key not in st.session_state:
                st.session_state[custom_model_input_key] = current_model if current_model not in model_options else ""

            previous_model_type = st.session_state.get("prev_user_mgmt_llm_model_type", st.session_state[model_type_key])
            selected_model_option = st.selectbox(
                "模型类型",
                options=model_keys,
                index=model_keys.index(st.session_state[model_type_key]) if st.session_state[model_type_key] in model_keys else 0,
                format_func=get_model_label,
                key=model_type_key
            )
            if selected_model_option == "__custom__" and previous_model_type != "__custom__":
                _reset_user_mgmt_llm_form_fields("user_mgmt_llm")
                st.session_state[model_type_key] = "__custom__"
            st.session_state["prev_user_mgmt_llm_model_type"] = st.session_state[model_type_key]
            custom_model_name = st.text_input(
                "自定义模型名",
                disabled=selected_model_option != "__custom__",
                placeholder="例如: gpt-5.4 / claude-3-opus / my-provider-model",
                key=custom_model_input_key
            )
            llm_api_key = st.text_input(
                "API Key",
                type="password",
                help="当前登录用户专属的大模型 API Key，系统分析将优先使用这里的配置。",
                key=api_key_input_key
            )
            llm_base_url = st.text_input(
                "Base URL",
                help="兼容 OpenAI 协议的接口地址，例如 DeepSeek、硅基流动、阿里百炼兼容地址。",
                key=base_url_input_key
            )
            llm_model = custom_model_name.strip() if selected_model_option == "__custom__" else selected_model_option
            if st.form_submit_button("保存当前用户大模型配置", type="primary"):
                ok, msg = update_user_llm_config(auth_user["id"], llm_api_key, llm_base_url, llm_model)
                (st.success if ok else st.error)(msg)
                if ok:
                    sync_runtime_llm_env({
                        "llm_api_key": llm_api_key,
                        "llm_base_url": llm_base_url,
                        "llm_model": llm_model,
                    })
                    st.rerun()
