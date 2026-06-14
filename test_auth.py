"""
auth 模块快速测试脚本
运行: python test_auth.py
"""
import sys

def test_mysql_connection():
    print("=" * 50)
    print("1. 测试 MySQL 连接")
    print("=" * 50)
    try:
        import pymysql
        conn = pymysql.connect(
            host="101.132.190.29",
            port=3306,
            user="root",
            password="Qsxzse66*",
            database="AIstock",
            connect_timeout=10,
        )
        conn.close()
        print("✅ MySQL 连接成功")
        return True
    except ImportError:
        print("❌ pymysql 未安装，请运行: python -m pip install pymysql")
        return False
    except Exception as e:
        print(f"❌ MySQL 连接失败: {e}")
        return False


def test_init_table():
    print("\n" + "=" * 50)
    print("2. 测试初始化 users 表")
    print("=" * 50)
    try:
        from auth import init_user_table
        init_user_table()
        print("✅ users 表初始化成功（已存在则跳过）")
        return True
    except Exception as e:
        print(f"❌ 初始化失败: {e}")
        return False


def test_default_admin_login():
    print("\n" + "=" * 50)
    print("3. 测试默认管理员登录 (admin / qsxzse66)")
    print("=" * 50)
    try:
        from auth import login
        user = login("admin", "qsxzse66")
        if user:
            print(f"✅ 登录成功: {user}")
            return True
        else:
            print("❌ 登录失败：用户名或密码错误")
            return False
    except Exception as e:
        print(f"❌ 登录异常: {e}")
        return False


def test_wrong_password():
    print("\n" + "=" * 50)
    print("4. 测试错误密码拒绝")
    print("=" * 50)
    try:
        from auth import login
        user = login("admin", "wrongpassword")
        if user is None:
            print("✅ 错误密码被正确拒绝")
            return True
        else:
            print("❌ 错误密码竟然通过了！")
            return False
    except Exception as e:
        print(f"❌ 异常: {e}")
        return False


def test_create_and_login_user():
    print("\n" + "=" * 50)
    print("5. 测试创建普通用户并登录")
    print("=" * 50)
    try:
        from auth import create_user, login, delete_user, get_all_users

        ok, msg = create_user("test_user_tmp", "test123456", "user")
        print(f"   创建用户: {'✅' if ok else '❌'} {msg}")

        if not ok:
            # 可能已存在，继续测试登录
            pass

        user = login("test_user_tmp", "test123456")
        if user:
            print(f"✅ 测试用户登录成功: {user}")
        else:
            print("❌ 测试用户登录失败")
            return False

        # 清理测试用户
        users = get_all_users()
        for u in users:
            if u["username"] == "test_user_tmp":
                ok2, msg2 = delete_user(u["id"])
                print(f"   清理测试用户: {'✅' if ok2 else '⚠️'} {msg2}")
                break

        return True
    except Exception as e:
        print(f"❌ 异常: {e}")
        return False


def test_list_users():
    print("\n" + "=" * 50)
    print("6. 查看当前所有用户")
    print("=" * 50)
    try:
        from auth import get_all_users
        users = get_all_users()
        if users:
            for u in users:
                status = "✅启用" if u["is_active"] else "🔴禁用"
                print(f"   [{u['id']}] {u['username']:15s} {u['role']:6s} {status}  创建:{str(u['created_at'])[:10]}")
        else:
            print("  （无用户）")
        return True
    except Exception as e:
        print(f"❌ 异常: {e}")
        return False


if __name__ == "__main__":
    results = []
    results.append(test_mysql_connection())
    if results[-1]:  # 连接成功才继续
        results.append(test_init_table())
        results.append(test_default_admin_login())
        results.append(test_wrong_password())
        results.append(test_create_and_login_user())
        results.append(test_list_users())

    print("\n" + "=" * 50)
    passed = sum(results)
    total = len(results)
    print(f"测试完成: {passed}/{total} 通过")
    if passed == total:
        print("🎉 所有测试通过！")
    print("=" * 50)
    sys.exit(0 if passed == total else 1)
