
## aitrader 项目结合 A_Share_investment_Agent 项目 AI 综合分析

### 快速开始

#### 1. 安装依赖
```bash
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

#### 2. 配置代理（推荐，防止 IP 被封）
编辑 `config/config.json`，启用代理配置：
```json
"PROXY_CONFIG": {
    "enable": true,                          // 改为 true 启用代理
    "http_proxy": "http://127.0.0.1:7890",   // 修改为你的代理地址
    "https_proxy": "http://127.0.0.1:7890"
}
```

**详细说明**: 查看 `代理配置快速指南.md`

#### 3. 运行程���
1. 先运行 `StockBasic.py` 生成最新的股票数据
2. 再运行 `main.py` 平台的策略

### 新功能
✅ **AkShare 代理配置** - 防止频繁请求导致 IP 被封
✅ **Baostock 数据源** - 替代 akshare.stock_zh_a_hist，更稳定
✅ **循环导入修复** - 解决模块导入问题

### TODO
# 1、增加 deepseek 分析选项，并把结果输出页面
# 2、增加主力资金监控预警通知

# A_Share_investment_Agent项目：AI分析新闻类比较强，默认Gemini模型免费，需切换vpn非香港,替换股票代码002444
# bash命令： 
conda activate quantAI  
poetry run python src/main.py --ticker 601567 --show-reasoning




    评分标准：
    1. 盈利能力(ROE>15% +1星)
    2. 估值水平(PE<30且PB<3 +1星)
    3. 资金热度(主力连续3日净流入 +3星)
    4. 技术形态(量价齐升 +3星)
    5. 行业地位(细分龙头 +1星)
    6. 信息面(热门利好 +1星)



#main.py 运行关键py文件：[page_tasks.py](gui/streamlit_pages/page_tasks.py)

# tips:
1、平台txt运行的A50_自选.txt可运行182条，其他数据有问题
2、格式化AI分析结果：notepad++  替换功能，查找：\\n替换为：\n   (勾选上扩展（X））


