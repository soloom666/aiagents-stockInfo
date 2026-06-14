# -*- coding: utf-8 -*-
"""
免费代理获取和测试工具
⚠️ 仅供测试使用，不推荐生产环境
"""
import requests
import time
import random
from concurrent.futures import ThreadPoolExecutor, as_completed


class ProxyTester:
    """代理测试器"""

    def __init__(self):
        self.valid_proxies = []

    @staticmethod
    def test_proxy(proxy, test_url='https://www.baidu.com', timeout=5):
        """
        测试代理是否可用

        Args:
            proxy: 代理地址，格式 "http://ip:port"
            test_url: 测试URL
            timeout: 超时时间（秒）

        Returns:
            tuple: (是否可用, 响应时间)
        """
        proxies = {
            'http': proxy,
            'https': proxy
        }

        try:
            start_time = time.time()
            response = requests.get(
                test_url,
                proxies=proxies,
                timeout=timeout,
                verify=False  # 忽略SSL验证
            )
            elapsed = time.time() - start_time

            if response.status_code == 200:
                return True, elapsed
            else:
                return False, 0

        except Exception as e:
            return False, 0

    def test_proxies_parallel(self, proxies, max_workers=10):
        """
        并行测试多个代理

        Args:
            proxies: 代理列表
            max_workers: 最大并发数

        Returns:
            list: 可用的代理列表
        """
        print(f"\n开始测试 {len(proxies)} 个代理（并发数: {max_workers}）...")
        valid_proxies = []

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有测试任务
            future_to_proxy = {
                executor.submit(self.test_proxy, proxy): proxy
                for proxy in proxies
            }

            # 收集结果
            for i, future in enumerate(as_completed(future_to_proxy), 1):
                proxy = future_to_proxy[future]
                try:
                    is_valid, elapsed = future.result()
                    status = "可用" if is_valid else "不可用"
                    print(f"[{i}/{len(proxies)}] {proxy}: {status}", end='')
                    if is_valid:
                        print(f" (响应时间: {elapsed:.2f}s)")
                        valid_proxies.append({
                            'proxy': proxy,
                            'response_time': elapsed
                        })
                    else:
                        print()
                except Exception as e:
                    print(f"[{i}/{len(proxies)}] {proxy}: 测试异常 - {e}")

        # 按响应时间排序
        valid_proxies.sort(key=lambda x: x['response_time'])

        return valid_proxies


def get_sample_free_proxies():
    """
    获取示例代理列表
    ⚠️ 这些是示例格式，实际IP��能已失效

    实际使用时，请：
    1. 访问免费代理网站（如 free-proxy-list.net）
    2. 手动复制最新的代理IP
    3. 或使用爬虫自动获取
    """
    print("\n⚠️  请手动从以下网站获取最新的免费代理：")
    print("  1. https://free-proxy-list.net/")
    print("  2. https://www.proxyscrape.com/free-proxy-list")
    print("  3. https://www.89ip.cn/")
    print("  4. https://www.kuaidaili.com/free/\n")

    # 示例格式（这些IP很可能已失效）
    sample_proxies = [
        "http://8.213.128.6:8080",
        "http://47.91.56.120:8080",
        "http://103.152.112.162:80",
        # 添加更多代理...
    ]

    print("以下是示例格式（可能已失效）:")
    for proxy in sample_proxies:
        print(f"  - {proxy}")

    return []  # 返回空列表，提示用户手动添加


def save_valid_proxies_to_config(valid_proxies, config_file='config/config.json'):
    """
    将可用代理保存到配置文件

    Args:
        valid_proxies: 可用代理列表
        config_file: 配置文件路径
    """
    if not valid_proxies:
        print("\n没有可用代理，不更新配置文件")
        return

    print(f"\n找到 {len(valid_proxies)} 个可用代理")
    print("\n可用代理列表（按响应时间排序）:")
    for i, item in enumerate(valid_proxies, 1):
        print(f"  {i}. {item['proxy']} (响应时间: {item['response_time']:.2f}s)")

    # 选择最快的代理
    fastest = valid_proxies[0]
    print(f"\n推荐使用最快的代理: {fastest['proxy']}")
    print(f"\n请手动编辑 {config_file}，设置:")
    print(f"""
"PROXY_CONFIG": {{
    "enable": true,
    "http_proxy": "{fastest['proxy']}",
    "https_proxy": "{fastest['proxy']}",
    "socks_proxy": ""
}}
""")


def manual_input_proxies():
    """手动输入代理进行测试"""
    print("\n" + "=" * 70)
    print("手动输入代理测试")
    print("=" * 70)
    print("\n请输入代理地址（格式: http://ip:port），每行一个，输入空行结束:")
    print("示例: http://8.213.128.6:8080\n")

    proxies = []
    while True:
        proxy = input("> ").strip()
        if not proxy:
            break
        if proxy.startswith('http://') or proxy.startswith('https://'):
            proxies.append(proxy)
            print(f"  已添加: {proxy}")
        else:
            print(f"  格式错误，请使用 http://ip:port 格式")

    return proxies


def main():
    """主函数"""
    print("=" * 70)
    print("免费代理获取和测试工具")
    print("=" * 70)
    print("\n⚠️  重要提示:")
    print("  - 免费代理不稳定，不推荐生产环境使用")
    print("  - 免费代理可能存在安全风险")
    print("  - 推荐使用本地代理工具（Clash）+ Baostock 数据源")
    print("=" * 70)

    # 初始化测试器
    tester = ProxyTester()

    # 选择代理来源
    print("\n请选择代理来源:")
    print("  1. 手动输入代理地址")
    print("  2. 查看推荐方案（无需免费代理）")
    print("  3. 退出")

    choice = input("\n请选择 (1/2/3): ").strip()

    if choice == '1':
        # 手动输入代理
        proxies = manual_input_proxies()

        if not proxies:
            print("\n没有输入任何代理，退出")
            return

        # 测试代理
        valid_proxies = tester.test_proxies_parallel(proxies, max_workers=5)

        # 保存结果
        if valid_proxies:
            save_valid_proxies_to_config(valid_proxies)
        else:
            print("\n所有代理都不可用，建议:")
            print("  1. 使用本地代理工具（Clash）")
            print("  2. 使用 Baostock 数据源（无需代理）")
            print("  3. 增加请求延迟")

    elif choice == '2':
        print("\n" + "=" * 70)
        print("推荐方案（无需免费代理）")
        print("=" * 70)
        print("\n方案1: 使用 Baostock（最推荐）⭐⭐⭐⭐⭐")
        print("  - 项目已集成 Baostock 数据源")
        print("  - 无需代理，稳定可靠")
        print("  - 使用方法: 直接运行项目即可")
        print("\n方案2: 使用本地代理工具（Clash）⭐⭐⭐⭐⭐")
        print("  - 下载 Clash Verge")
        print("  - 配置订阅链接")
        print("  - 默认端口: 7890")
        print("  - 在 config.json 中配置:")
        print('    "http_proxy": "http://127.0.0.1:7890"')
        print("\n方案3: 增加请求延迟 ⭐⭐⭐⭐")
        print("  - 调大请求间隔（5-10秒）")
        print("  - 降低被封概率")
        print("\n详细说明请查看: 代理获取方案.md")

    else:
        print("\n退出")


if __name__ == '__main__':
    # 禁用 SSL 警告
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    main()
