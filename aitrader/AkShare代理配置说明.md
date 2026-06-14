# AkShare 代理配置说明

## 为什么需要配置代理？

在频繁调用 akshare 接口时，可能会遇到以下问题：
- IP 被暂时封禁
- 请求速度受限
- 连接超时或拒绝

通过配置代理，可以：
- 避免 IP 被封
- 提高访问成功率
- 绕过网络限制

## 配置步骤

### 1. 修改配置文件

编辑 `config/config.json`，找到 `PROXY_CONFIG` 部分：

```json
{
    "PROXY_CONFIG": {
        "enable": true,                           // 是否启用代理
        "http_proxy": "http://127.0.0.1:7890",    // HTTP 代理地址
        "https_proxy": "http://127.0.0.1:7890",   // HTTPS 代理地址
        "socks_proxy": "socks5://127.0.0.1:7890"  // SOCKS5 代理地址（可选）
    }
}
```

### 2. 配置说明

#### 启用/禁用代理
```json
"enable": true   // 启用代理
"enable": false  // 禁用代理（直连网络）
```

#### HTTP/HTTPS 代理
适用于大多数代理工具（如 Clash、V2Ray、SSR 等）：
```json
"http_proxy": "http://127.0.0.1:7890",
"https_proxy": "http://127.0.0.1:7890"
```

#### SOCKS5 代理
如果只使用 SOCKS5 代理，需要安装 `pysocks` 库：
```bash
pip install pysocks
```

配置示例：
```json
"http_proxy": "",
"https_proxy": "",
"socks_proxy": "socks5://127.0.0.1:1080"
```

### 3. 常见代理工具的端口

| 代理工具 | 默认端口 | 代理类型 |
|---------|---------|---------|
| Clash | 7890 | HTTP/HTTPS |
| V2Ray | 10808 | HTTP/HTTPS |
| SSR | 1080 | SOCKS5 |
| Shadowsocks | 1080 | SOCKS5 |
| Clash Verge | 7890 | HTTP/HTTPS |

**注意**：具体端口以你的代理工具配置为准。

## 使用示例

### 示例1：使用 Clash 代理

```json
{
    "PROXY_CONFIG": {
        "enable": true,
        "http_proxy": "http://127.0.0.1:7890",
        "https_proxy": "http://127.0.0.1:7890",
        "socks_proxy": ""
    }
}
```

### 示例2：使用公司代理

```json
{
    "PROXY_CONFIG": {
        "enable": true,
        "http_proxy": "http://proxy.company.com:8080",
        "https_proxy": "http://proxy.company.com:8080",
        "socks_proxy": ""
    }
}
```

### 示例3：使用带认证的代理

```json
{
    "PROXY_CONFIG": {
        "enable": true,
        "http_proxy": "http://username:password@proxy.com:8080",
        "https_proxy": "http://username:password@proxy.com:8080",
        "socks_proxy": ""
    }
}
```

### 示例4：禁用代理（直连）

```json
{
    "PROXY_CONFIG": {
        "enable": false,
        "http_proxy": "",
        "https_proxy": "",
        "socks_proxy": ""
    }
}
```

## 代理工作原理

### 自动初始化
代理配置会在以下时机自动初始化：
1. 导入 `stocks_Info` 模块时
2. 运行 `ai_analysis_run.py` 时
3. 运行 `A_Share_investment_Agent` 时

### 环境变量设置
代理模块会自动设置以下环境变量：
- `HTTP_PROXY` - HTTP 请求��理
- `HTTPS_PROXY` - HTTPS 请求代理

akshare 内部使用 `requests` 库，会自动读取这些环境变量。

## 测试代理配置

### 测试1：运行代理配置测试
```bash
cd "E:\project\Python project\platform\aitrader"
python common/proxy_config.py
```

输出示例：
```
============================================================
测试代理配置模块
============================================================

代理状态:
  已初始化: True
  已启用: True
  HTTP_PROXY: http://127.0.0.1:7890
  HTTPS_PROXY: http://127.0.0.1:7890

代理字典: {'http': 'http://127.0.0.1:7890', 'https': 'http://127.0.0.1:7890'}
```

### 测试2：运行项目测试
```bash
python test_import_fix.py
```

查看日志中是否有代理初始化信息：
```
设置 HTTP_PROXY: http://127.0.0.1:7890
设置 HTTPS_PROXY: http://127.0.0.1:7890
✓ akshare 代理配置初始化成功
```

### 测试3：验证 akshare 请求
```python
import akshare as ak
from common.proxy_config import ProxyConfig

# 初始化代理
ProxyConfig.init_akshare_proxy()

# 测试获取数据
df = ak.stock_zh_a_spot_em()
print(f"成功获取 {len(df)} 条数据")
```

## 代理 API 使用

### 获取代理状态
```python
from common.proxy_config import ProxyConfig

status = ProxyConfig.get_proxy_status()
print(status)
# 输出: {'initialized': True, 'enabled': True, 'http_proxy': '...', 'https_proxy': '...'}
```

### 临时禁用代理
```python
from common.proxy_config import ProxyConfig

# 禁用代理
ProxyConfig.disable_proxy()

# 你的代码（直连网络）
# ...

# 重新启用代理
ProxyConfig.enable_proxy()
```

### 获取代理字典（用于 requests）
```python
from common.proxy_config import ProxyConfig
import requests

proxies = ProxyConfig.get_proxies_dict()
# proxies = {'http': 'http://127.0.0.1:7890', 'https': 'http://127.0.0.1:7890'}

# 在 requests 中使用
response = requests.get('https://api.example.com', proxies=proxies)
```

## 常见问题

### Q1: 配置了代理但还是被封？
**解决方案：**
1. 检查代理是否正常工作
2. 增加请求间隔时间
3. 使用随机延迟
4. 更换代理 IP

### Q2: 启用代理后连接超时？
**解决方案：**
1. 检查代理地址和端口是否正确
2. 确认代理工具是否正在运行
3. 测试代理连接：`curl -x http://127.0.0.1:7890 https://www.baidu.com`

### Q3: 如何知道代理是否生效？
**解决方案：**
1. 查看日志，确认有 "✓ akshare 代理配置初始化成功" 信息
2. 在代理工具中查看连接记录
3. 运行测试脚本验证

### Q4: SOCKS5 代理报错？
**解决方案：**
```bash
pip install pysocks
```

如果还有问题，改用 HTTP/HTTPS 代理。

### Q5: 需要为不同的接口使用不同的代理？
**解决方案：**
当前方案是全局代理，如需细粒度控制：
```python
from common.proxy_config import ProxyConfig
import akshare as ak

# 临时禁用代理
ProxyConfig.disable_proxy()
df1 = ak.some_function()  # 直连

# 启用代理
ProxyConfig.enable_proxy()
df2 = ak.another_function()  # 使用代理
```

## 代理推荐

### 免费代理
- 不推荐：不稳定、速度慢、容易泄露数据

### 付费代理
- **推荐**：稳定、速度快、IP 池大
- 适合长期使用

### 本地代理工具
- **Clash**（推荐）：简单易用，支持订阅
- **V2Ray**：功能强大，配置复杂
- **Clash Verge**：美观，易用

## 安全提示

1. **不要**在代码中硬编码代理密码
2. **不要**提交包含代理配置的 `config.json` 到公共仓库
3. **建议**将 `config.json` 添加到 `.gitignore`
4. **建议**使用环境变量管理敏感信息

## 进阶配置

### 为特定域名设置代理
修改 `proxy_config.py`，添加 `NO_PROXY` 环境变量：
```python
os.environ['NO_PROXY'] = 'localhost,127.0.0.1,.local'
```

### 动态切换代理
```python
from common.proxy_config import ProxyConfig
import os

# 切换到代理1
os.environ['HTTP_PROXY'] = 'http://proxy1.com:8080'
os.environ['HTTPS_PROXY'] = 'http://proxy1.com:8080'

# 切换到代理2
os.environ['HTTP_PROXY'] = 'http://proxy2.com:8080'
os.environ['HTTPS_PROXY'] = 'http://proxy2.com:8080'
```

## 总结

- ✅ 配置简单：只需修改 `config.json`
- ✅ 自动初始化：导入模块时自动加载
- ✅ 灵活控制：支持启用/禁用/动态切换
- ✅ 日志完善：方便调试和排错

---

**最后更新**：2026-02-11
**版本**：v1.0
