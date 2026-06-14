# -*- coding: utf-8 -*-
"""
AkShare 代理配置模块
统一管理项目中 akshare 的代理设置，防止 IP 被封
"""
import os
import sys
from common.readFile import ReadFile
from common.logger import logger


class ProxyConfig:
    """代理配置管理类"""

    _initialized = False
    _proxy_enabled = False

    @classmethod
    def init_akshare_proxy(cls):
        """
        初始化 akshare 代理配置

        说明：
        - 从 config.json 读取代理配置
        - 设置环境变量 HTTP_PROXY 和 HTTPS_PROXY
        - akshare 内部使用 requests 库，会自动读取环境变量中的代理设置
        """
        if cls._initialized:
            logger.info("代理配置已初始化，跳过重复初始化")
            return

        try:
            # 读取配置文件
            config = ReadFile.read_json()
            proxy_config = config.get('PROXY_CONFIG', {})

            # 检查是否启用代理
            enable = proxy_config.get('enable', False)

            if not enable:
                logger.info("代理配置未启用（enable=false），akshare 将直连网络")
                cls._initialized = True
                cls._proxy_enabled = False
                return

            # 获取代理地址
            http_proxy = proxy_config.get('http_proxy', '')
            https_proxy = proxy_config.get('https_proxy', '')
            socks_proxy = proxy_config.get('socks_proxy', '')

            # 设置环境变量（优先使用 HTTP/HTTPS 代理）
            if http_proxy:
                os.environ['HTTP_PROXY'] = http_proxy
                logger.info(f"设置 HTTP_PROXY: {http_proxy}")

            if https_proxy:
                os.environ['HTTPS_PROXY'] = https_proxy
                logger.info(f"设置 HTTPS_PROXY: {https_proxy}")

            # 如果使用 SOCKS 代理，需要安装 pysocks 库
            if socks_proxy and not (http_proxy or https_proxy):
                os.environ['HTTP_PROXY'] = socks_proxy
                os.environ['HTTPS_PROXY'] = socks_proxy
                logger.info(f"设置 SOCKS 代理: {socks_proxy}")
                logger.warning("使用 SOCKS 代理需要安装 pysocks: pip install pysocks")

            cls._initialized = True
            cls._proxy_enabled = True
            logger.info("✓ akshare 代理配置初始化成功")

        except Exception as e:
            logger.error(f"初始化代理配置失败: {str(e)}")
            logger.info("akshare 将使用直连网络")
            cls._initialized = True
            cls._proxy_enabled = False

    @classmethod
    def disable_proxy(cls):
        """临时禁用代理"""
        if 'HTTP_PROXY' in os.environ:
            del os.environ['HTTP_PROXY']
            logger.info("已禁用 HTTP_PROXY")

        if 'HTTPS_PROXY' in os.environ:
            del os.environ['HTTPS_PROXY']
            logger.info("已禁用 HTTPS_PROXY")

        cls._proxy_enabled = False
        logger.info("代理已禁用")

    @classmethod
    def enable_proxy(cls):
        """重新启用代理"""
        cls._initialized = False
        cls.init_akshare_proxy()

    @classmethod
    def get_proxy_status(cls):
        """获取代理状态"""
        return {
            'initialized': cls._initialized,
            'enabled': cls._proxy_enabled,
            'http_proxy': os.environ.get('HTTP_PROXY', None),
            'https_proxy': os.environ.get('HTTPS_PROXY', None)
        }

    @classmethod
    def get_proxies_dict(cls):
        """
        获取代理字典（用于 requests 库）

        返回格式:
        {
            'http': 'http://127.0.0.1:7890',
            'https': 'http://127.0.0.1:7890'
        }
        """
        if not cls._proxy_enabled:
            return None

        proxies = {}
        if 'HTTP_PROXY' in os.environ:
            proxies['http'] = os.environ['HTTP_PROXY']
        if 'HTTPS_PROXY' in os.environ:
            proxies['https'] = os.environ['HTTPS_PROXY']

        return proxies if proxies else None


# 自动初始化（在模块导入时执行一次）
def auto_init_proxy():
    """自动初始化代理配置"""
    try:
        ProxyConfig.init_akshare_proxy()
    except Exception as e:
        logger.warning(f"自动初始化代理失败: {str(e)}")


# 模块导入时自动初始化
if __name__ != '__main__':
    # 只在非直接运行时自动初始化
    pass  # 改为手动初始化，避免导入时的副作用


# 测试代码
if __name__ == '__main__':
    print("=" * 60)
    print("测试代理配置模块")
    print("=" * 60)

    # 初始化代理
    ProxyConfig.init_akshare_proxy()

    # 获取代理状态
    status = ProxyConfig.get_proxy_status()
    print("\n代理状态:")
    print(f"  已初始化: {status['initialized']}")
    print(f"  已启用: {status['enabled']}")
    print(f"  HTTP_PROXY: {status['http_proxy']}")
    print(f"  HTTPS_PROXY: {status['https_proxy']}")

    # 获取代理字典
    proxies = ProxyConfig.get_proxies_dict()
    print(f"\n代理字典: {proxies}")

    # 测试禁用代理
    print("\n测试禁用代理...")
    ProxyConfig.disable_proxy()
    status = ProxyConfig.get_proxy_status()
    print(f"  禁用后状态: {status['enabled']}")

    # 测试重新启用
    print("\n测试重新启用代理...")
    ProxyConfig.enable_proxy()
    status = ProxyConfig.get_proxy_status()
    print(f"  启用后状态: {status['enabled']}")

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)
