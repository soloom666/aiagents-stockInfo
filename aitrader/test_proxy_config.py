# -*- coding: utf-8 -*-
"""
测试 AkShare 代理配置
"""
import sys
import os

# 添加项目根目录到 Python 路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)


def test_proxy_module():
    """测试代理配置模块"""
    print("=" * 70)
    print("测试1: 代理配置模块")
    print("=" * 70)

    try:
        from common.proxy_config import ProxyConfig

        # 初始化代理
        ProxyConfig.init_akshare_proxy()

        # 获取代理状态
        status = ProxyConfig.get_proxy_status()
        print("\n代理状态:")
        print(f"  [*] 已初始化: {status['initialized']}")
        print(f"  [*] 已启用: {status['enabled']}")
        print(f"  [*] HTTP_PROXY: {status['http_proxy'] or '未设置'}")
        print(f"  [*] HTTPS_PROXY: {status['https_proxy'] or '未设置'}")

        # 获取代理字典
        proxies = ProxyConfig.get_proxies_dict()
        if proxies:
            print(f"\n代理字典:")
            for key, value in proxies.items():
                print(f"  [*] {key}: {value}")
        else:
            print("\n[提示] 未配置代理或代理未启用")

        return True

    except Exception as e:
        print(f"\n[错误] 代理配置模块测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_akshare_with_proxy():
    """测试 akshare 使用代理获取数据"""
    print("\n" + "=" * 70)
    print("测试2: AkShare 使用代理获取数据")
    print("=" * 70)

    try:
        # 初始化代理（如果之前未初始化）
        from common.proxy_config import ProxyConfig
        ProxyConfig.init_akshare_proxy()

        import akshare as ak
        import time

        print("\n[开始] 测试获取 A 股实时行情数据...")
        start_time = time.time()

        # 获取少量数据进行测试
        df = ak.stock_zh_a_spot_em()

        end_time = time.time()
        elapsed = end_time - start_time

        if df is not None and not df.empty:
            print(f"[成功] 获取数据成功")
            print(f"  [*] 数据条数: {len(df)}")
            print(f"  [*] 耗时: {elapsed:.2f} 秒")
            print(f"  [*] 数据列: {df.columns.tolist()[:5]}...")  # 只显示前5列
            print(f"\n前3条数据:")
            print(df.head(3)[['代码', '名称', '最新价', '涨跌幅']].to_string(index=False))
            return True
        else:
            print("[失败] 获取的数据为空")
            return False

    except Exception as e:
        print(f"\n[错误] AkShare 数据获取失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_proxy_toggle():
    """测试代理的启用/禁用切换"""
    print("\n" + "=" * 70)
    print("测试3: 代理启用/禁用切换")
    print("=" * 70)

    try:
        from common.proxy_config import ProxyConfig

        # 禁用代理
        print("\n[操作] 禁用代理...")
        ProxyConfig.disable_proxy()
        status = ProxyConfig.get_proxy_status()
        print(f"  [*] 代理状态: {'已禁用' if not status['enabled'] else '已启用'}")

        # 重新启用代理
        print("\n[操作] 重新启用代理...")
        ProxyConfig.enable_proxy()
        status = ProxyConfig.get_proxy_status()
        print(f"  [*] 代理状态: {'已启用' if status['enabled'] else '已禁用'}")

        return True

    except Exception as e:
        print(f"\n[错误] 代理切换测试失败: {e}")
        return False


def test_environment_variables():
    """测试环境变量是否正确设置"""
    print("\n" + "=" * 70)
    print("测试4: 环境变量检查")
    print("=" * 70)

    import os

    env_vars = ['HTTP_PROXY', 'HTTPS_PROXY', 'NO_PROXY']

    print("\n当前环境变量:")
    for var in env_vars:
        value = os.environ.get(var, None)
        if value:
            print(f"  [*] {var}: {value}")
        else:
            print(f"  [-] {var}: 未设置")

    return True


def main():
    """主测试函数"""
    print("\n" + "=" * 70)
    print("AkShare 代理配置 - 完整测试")
    print("=" * 70)

    results = {}

    # 测试1: 代理配置模块
    results['proxy_module'] = test_proxy_module()

    # 测试2: AkShare 获取数据
    results['akshare_data'] = test_akshare_with_proxy()

    # 测试3: 代理切换
    results['proxy_toggle'] = test_proxy_toggle()

    # 测试4: 环境变量
    results['env_vars'] = test_environment_variables()

    # 总结
    print("\n" + "=" * 70)
    print("测试总结")
    print("=" * 70)

    print("\n测试结果:")
    for test_name, result in results.items():
        status = "[通过]" if result else "[失败]"
        print(f"  {status} {test_name}")

    all_passed = all(results.values())

    print("\n" + "=" * 70)
    if all_passed:
        print("[成功] 所有测试通过！代理配置正常工作")
    else:
        print("[警告] 部分测试失败，请检查配置")
    print("=" * 70)

    # 使用说明
    print("\n使用说明:")
    print("1. 确保 config.json 中的 PROXY_CONFIG.enable 设置正确")
    print("2. 检查代理地址和端口是否正确")
    print("3. 确认代理工具（如 Clash）是否正在运行")
    print("4. 如果测试失败，查看上方的错误信息进行排查")
    print("\n详细配置说明请查看: AkShare代理配置说明.md")
    print("=" * 70)


if __name__ == '__main__':
    main()
