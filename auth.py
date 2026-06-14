"""
用户认证模块 - 基于 MySQL AIstock 数据库
"""
from __future__ import annotations

import hashlib
import hmac
import os
import time
import pymysql
import pymysql.cursors
from datetime import datetime
from typing import Any


# MySQL 连接配置
DB_CONFIG = {
    "host": "101.132.190.29",
    "port": 3306,
    "user": "root",
    "password": "Qsxzse66*",
    "database": "AIstock",
    "charset": "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor,
    "connect_timeout": 10,
    "read_timeout": 10,
    "write_timeout": 10,
    "autocommit": True,
}

# 默认管理员账号（首次启动时自动创建）
DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_PASSWORD = "admin123"
ROLE_OPTIONS = ("admin", "user", "vip")
DEFAULT_LLM_BASE_URL = "https://api.deepseek.com/v1"


def _get_conn():
    """获取 MySQL 连接"""
    return pymysql.connect(**DB_CONFIG)


def get_role_label(role: str) -> str:
    role_map = {
        "admin": "管理员",
        "user": "普通用户",
        "vip": "VIP",
    }
    return role_map.get(role, role)


def sync_runtime_llm_env(user_or_config: dict | None) -> None:
    """将当前用户的大模型配置同步到进程环境变量，供运行时统一读取。"""
    llm_config = user_or_config or {}
    os.environ["APP_USER_LLM_API_KEY"] = (llm_config.get("llm_api_key") or "").strip()
    os.environ["APP_USER_LLM_BASE_URL"] = (llm_config.get("llm_base_url") or DEFAULT_LLM_BASE_URL).strip()
    os.environ["APP_USER_LLM_MODEL"] = (llm_config.get("llm_model") or "deepseek-chat").strip()


def clear_runtime_llm_env() -> None:
    """清理当前进程中的用户大模型配置。"""
    for key in ("APP_USER_LLM_API_KEY", "APP_USER_LLM_BASE_URL", "APP_USER_LLM_MODEL"):
        os.environ.pop(key, None)


def get_runtime_llm_config() -> dict[str, str]:
    """优先从当前登录用户读取大模型配置，回退到进程环境变量。"""
    config = {
        "api_key": os.getenv("APP_USER_LLM_API_KEY", "").strip(),
        "base_url": os.getenv("APP_USER_LLM_BASE_URL", DEFAULT_LLM_BASE_URL).strip() or DEFAULT_LLM_BASE_URL,
        "model": os.getenv("APP_USER_LLM_MODEL", "deepseek-chat").strip() or "deepseek-chat",
    }

    try:
        import streamlit as st
        user = st.session_state.get("auth_user") if hasattr(st, "session_state") else None
        if user:
            config["api_key"] = (user.get("llm_api_key") or config["api_key"]).strip()
            config["base_url"] = (user.get("llm_base_url") or config["base_url"]).strip() or DEFAULT_LLM_BASE_URL
            config["model"] = (user.get("llm_model") or config["model"]).strip() or "deepseek-chat"
    except Exception:
        pass

    return config


def _refresh_session_user(user_id: int) -> None:
    """如果当前会话就是该用户，刷新 session 中的用户信息。"""
    try:
        import streamlit as st
        session_user = st.session_state.get("auth_user") if hasattr(st, "session_state") else None
        if not session_user or session_user.get("id") != user_id:
            return
        latest_user = get_user_by_id(user_id)
        if latest_user:
            st.session_state.auth_user = latest_user
            sync_runtime_llm_env(latest_user)
    except Exception:
        pass


def _is_lock_timeout_error(exc: Exception) -> bool:
    return isinstance(exc, pymysql.err.OperationalError) and len(exc.args) > 0 and exc.args[0] == 1205


def _update_last_login_with_retry(user_id: int, max_retries: int = 2) -> None:
    """尽量更新最后登录时间，锁等待超时时短暂重试，不影响登录主流程。"""
    for attempt in range(max_retries + 1):
        conn = _get_conn()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "UPDATE users SET last_login = %s WHERE id = %s",
                    (datetime.now(), user_id),
                )
            return
        except Exception as exc:
            if not _is_lock_timeout_error(exc) or attempt >= max_retries:
                return
            time.sleep(0.2 * (attempt + 1))
        finally:
            conn.close()


def _hash_password(password: str, salt: str = None) -> tuple[str, str]:
    """SHA-256 加盐哈希密码，返回 (hash, salt)"""
    if salt is None:
        salt = os.urandom(16).hex()
    pw_hash = hashlib.sha256((password + salt).encode("utf-8")).hexdigest()
    return pw_hash, salt


# session token 签名密钥（进程级随机生成，重启后所有 token 失效，需重新登录）
_SESSION_SECRET = os.urandom(32).hex()
_TOKEN_VALIDITY_SECONDS = 7 * 24 * 3600  # 7 天


def generate_session_token(user_id: int) -> str:
    """生成带签名的 session token，格式: user_id.expiry.salt.signature"""
    expiry = int(time.time()) + _TOKEN_VALIDITY_SECONDS
    salt = os.urandom(8).hex()
    payload = f"{user_id}.{expiry}.{salt}"
    sig = hmac.new(_SESSION_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()[:32]
    return f"{payload}.{sig}"


def validate_session_token(token: str) -> dict | None:
    """验证 session token，成功返回用户信息字典，失败返回 None"""
    try:
        parts = token.rsplit(".", 1)
        if len(parts) != 2:
            return None
        payload, sig = parts
        expected_sig = hmac.new(_SESSION_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()[:32]
        if not hmac.compare_digest(sig, expected_sig):
            return None
        user_id_str, expiry_str, _salt = payload.split(".", 2)
        user_id = int(user_id_str)
        expiry = int(expiry_str)
        if time.time() > expiry:
            return None
        return get_user_by_id(user_id)
    except (ValueError, AttributeError):
        return None


def init_user_table():
    """初始化 users 表，如不存在则创建，并创建默认管理员"""
    conn = _get_conn()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id          INT AUTO_INCREMENT PRIMARY KEY,
                    username    VARCHAR(50)  UNIQUE NOT NULL,
                    password_hash VARCHAR(64) NOT NULL,
                    salt        VARCHAR(32)  NOT NULL,
                    role        ENUM('admin','user','vip') NOT NULL DEFAULT 'user',
                    is_active   TINYINT(1)   NOT NULL DEFAULT 1,
                    llm_api_key TEXT NULL,
                    llm_base_url VARCHAR(255) NULL,
                    llm_model   VARCHAR(120) NULL,
                    created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    last_login  DATETIME     NULL
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """)
            conn.commit()

            cursor.execute("SHOW COLUMNS FROM users LIKE 'role'")
            role_column = cursor.fetchone()
            if role_column and "vip" not in str(role_column.get("Type", "")):
                cursor.execute(
                    "ALTER TABLE users MODIFY COLUMN role ENUM('admin','user','vip') NOT NULL DEFAULT 'user'"
                )
                conn.commit()

            cursor.execute("SHOW COLUMNS FROM users LIKE 'llm_api_key'")
            if cursor.fetchone() is None:
                cursor.execute("ALTER TABLE users ADD COLUMN llm_api_key TEXT NULL AFTER is_active")
                conn.commit()

            cursor.execute("SHOW COLUMNS FROM users LIKE 'llm_base_url'")
            if cursor.fetchone() is None:
                cursor.execute("ALTER TABLE users ADD COLUMN llm_base_url VARCHAR(255) NULL AFTER llm_api_key")
                conn.commit()

            cursor.execute("SHOW COLUMNS FROM users LIKE 'llm_model'")
            if cursor.fetchone() is None:
                cursor.execute("ALTER TABLE users ADD COLUMN llm_model VARCHAR(120) NULL AFTER llm_base_url")
                conn.commit()

            # 若无任何用户，则创建默认管理员
            cursor.execute("SELECT COUNT(*) AS cnt FROM users")
            if cursor.fetchone()["cnt"] == 0:
                pw_hash, salt = _hash_password(DEFAULT_ADMIN_PASSWORD)
                cursor.execute(
                    "INSERT INTO users (username, password_hash, salt, role) VALUES (%s, %s, %s, 'admin')",
                    (DEFAULT_ADMIN_USERNAME, pw_hash, salt),
                )
                conn.commit()
    finally:
        conn.close()


def login(username: str, password: str) -> dict | None:
    """
    验证用户名和密码。
    成功返回用户信息字典，失败返回 None。
    """
    conn = _get_conn()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM users WHERE username = %s AND is_active = 1",
                (username,),
            )
            user = cursor.fetchone()
            if user is None:
                return None
            pw_hash, _ = _hash_password(password, user["salt"])
            if pw_hash != user["password_hash"]:
                return None
            last_login_at = datetime.now()
            _update_last_login_with_retry(user["id"])
            return {
                "id": user["id"],
                "username": user["username"],
                "role": user["role"],
                "llm_api_key": user.get("llm_api_key") or "",
                "llm_base_url": user.get("llm_base_url") or DEFAULT_LLM_BASE_URL,
                "llm_model": user.get("llm_model") or "deepseek-chat",
                "created_at": str(user["created_at"]),
                "last_login": str(last_login_at),
            }
    finally:
        conn.close()


def create_user(username: str, password: str, role: str = "user") -> tuple[bool, str]:
    """
    创建新用户。
    返回 (success, message)。
    """
    if not username or not password:
        return False, "用户名和密码不能为空"
    if len(username) < 2 or len(username) > 50:
        return False, "用户名长度应在 2-50 个字符之间"
    if len(password) < 6:
        return False, "密码长度不能少于 6 位"
    if role not in ROLE_OPTIONS:
        return False, "角色必须为 admin、user 或 vip"

    conn = _get_conn()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
            if cursor.fetchone():
                return False, f"用户名 '{username}' 已存在"
            pw_hash, salt = _hash_password(password)
            cursor.execute(
                "INSERT INTO users (username, password_hash, salt, role) VALUES (%s, %s, %s, %s)",
                (username, pw_hash, salt, role),
            )
            conn.commit()
            return True, f"用户 '{username}' 创建成功"
    except Exception as e:
        return False, f"创建用户失败: {str(e)}"
    finally:
        conn.close()


def get_all_users() -> list[dict]:
    """获取所有用户列表（不含密码字段）"""
    conn = _get_conn()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT id, username, role, is_active, llm_base_url, llm_model, created_at, last_login FROM users ORDER BY id"
            )
            return cursor.fetchall()
    finally:
        conn.close()


def get_user_by_id(user_id: int) -> dict[str, Any] | None:
    """根据用户ID获取用户信息。"""
    conn = _get_conn()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, username, role, is_active, llm_api_key, llm_base_url, llm_model,
                       created_at, last_login
                FROM users
                WHERE id = %s
                """,
                (user_id,),
            )
            user = cursor.fetchone()
            if not user:
                return None
            user["llm_api_key"] = user.get("llm_api_key") or ""
            user["llm_base_url"] = user.get("llm_base_url") or DEFAULT_LLM_BASE_URL
            user["llm_model"] = user.get("llm_model") or "deepseek-chat"
            return user
    finally:
        conn.close()


def set_user_active(user_id: int, is_active: bool) -> tuple[bool, str]:
    """启用或禁用用户"""
    conn = _get_conn()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "UPDATE users SET is_active = %s WHERE id = %s",
                (1 if is_active else 0, user_id),
            )
            conn.commit()
            action = "启用" if is_active else "禁用"
            return True, f"用户已{action}"
    except Exception as e:
        return False, str(e)
    finally:
        conn.close()


def change_role(user_id: int, role: str) -> tuple[bool, str]:
    """修改用户角色"""
    if role not in ROLE_OPTIONS:
        return False, "无效角色"
    conn = _get_conn()
    try:
        with conn.cursor() as cursor:
            cursor.execute("UPDATE users SET role = %s WHERE id = %s", (role, user_id))
            conn.commit()
            _refresh_session_user(user_id)
            return True, "角色修改成功"
    except Exception as e:
        return False, str(e)
    finally:
        conn.close()


def update_user_llm_config(user_id: int, api_key: str, base_url: str, model: str) -> tuple[bool, str]:
    """保存用户专属大模型配置。"""
    normalized_api_key = (api_key or "").strip()
    normalized_base_url = (base_url or "").strip() or DEFAULT_LLM_BASE_URL
    normalized_model = (model or "").strip() or "deepseek-chat"

    if not normalized_api_key:
        return False, "API Key 不能为空"
    if len(normalized_api_key) < 10:
        return False, "API Key 格式不正确"
    if not normalized_base_url.startswith(("http://", "https://")):
        return False, "Base URL 必须以 http:// 或 https:// 开头"
    if not normalized_model:
        return False, "模型不能为空"
    if normalized_model == "__custom__":
        return False, "请选择具体模型或填写自定义模型名"

    conn = _get_conn()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE users
                SET llm_api_key = %s, llm_base_url = %s, llm_model = %s
                WHERE id = %s
                """,
                (normalized_api_key, normalized_base_url, normalized_model, user_id),
            )
            conn.commit()
            _refresh_session_user(user_id)
            return True, "大模型配置已保存"
    except Exception as e:
        return False, str(e)
    finally:
        conn.close()


def change_password(user_id: int, new_password: str) -> tuple[bool, str]:
    """重置用户密码"""
    if len(new_password) < 6:
        return False, "密码长度不能少于 6 位"
    pw_hash, salt = _hash_password(new_password)
    conn = _get_conn()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "UPDATE users SET password_hash = %s, salt = %s WHERE id = %s",
                (pw_hash, salt, user_id),
            )
            conn.commit()
            return True, "密码修改成功"
    except Exception as e:
        return False, str(e)
    finally:
        conn.close()


def delete_user(user_id: int) -> tuple[bool, str]:
    """删除用户（不可删除最后一个 admin）"""
    conn = _get_conn()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT role FROM users WHERE id = %s", (user_id,)
            )
            user = cursor.fetchone()
            if not user:
                return False, "用户不存在"
            if user["role"] == "admin":
                cursor.execute("SELECT COUNT(*) AS cnt FROM users WHERE role = 'admin'")
                if cursor.fetchone()["cnt"] <= 1:
                    return False, "不能删除最后一个管理员账号"
            cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
            conn.commit()
            return True, "用户已删除"
    except Exception as e:
        return False, str(e)
    finally:
        conn.close()


# 模块加载时初始化表结构
try:
    init_user_table()
except Exception as _init_err:
    print(f"[auth] 数据库初始化失败: {_init_err}")
