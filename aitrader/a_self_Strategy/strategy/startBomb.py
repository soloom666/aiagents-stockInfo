


"""

安装AKShare并获取A股全量数据
# 安装AKShare（需Python≥3.7）
pip install akshare

# 获取全市场股票列表（排除ST、科创板）
import akshare as ak

# 获取全A股代码及名称
stock_list = ak.stock_info_a_code_name()
stock_list = stock_list[~stock_list['code'].str.contains('ST')]  # 排除ST股
stock_list = stock_list[~stock_list['code'].str.startswith('688')]  # 排除科创板
2. 获取个股历史行情数据
def get_stock_history(code, start_date='20240101', end_date='20250613'):
    df = ak.stock_zh_a_daily(symbol=code, start_date=start_date, end_date=end_date, adjust="qfq")
    # 计算技术指标
    df['vol_ma5'] = df['volume'].rolling(5).mean()  # 5日成交量均线
    df['close_ma60'] = df['close'].rolling(60).mean()  # 60日均线
    df['ma5_ma60_ratio'] = df['close_ma5'] / df['close_ma60']  # 5日与60日均线比值
    return df

# 示例：获取贵州茅台数据
df_600519 = get_stock_history('sh600519')  
"""


"""
二、妖股起爆点筛选条件设计
1. 核心指标（基于技术分析与市场情绪）
成交量突变：当日成交量 > 前5日均量的3倍。
均线突破：收盘价突破60日均线，且5日均线上穿60日均线。
MACD金叉：MACD线（DIFF）上穿信号线（DEA），且红柱放大。
换手率异常：单日换手率 >8%（中小盘股）或 >5%（大盘股）。


def detect_breakout(df):
    signals = []
    for i in range(1, len(df)):
        # 成交量突变条件
        vol_ratio = df['volume'].iloc[i] / df['vol_ma5'].iloc[i-1]
        # 均线突破条件
        ma_break = (df['close'].iloc[i] > df['close_ma60'].iloc[i]) and \
                   (df['ma5_ma60_ratio'].iloc[i] > 1.05)
        # MACD条件（需提前计算MACD）
        macd_diff = df['macd_diff'].iloc[i]
        macd_signal = df['macd_signal'].iloc[i]
        macd_golden_cross = (macd_diff > macd_signal) and (df['macd_diff'].iloc[i-1] < df['macd_signal'].iloc[i-1])
        # 换手率条件
        turnover_condition = df['turnover_rate'].iloc[i] > 8

        if vol_ratio > 3 and ma_break and macd_golden_cross and turnover_condition:
            signals.append(df.index[i])
    return signals

# 应用至全市场股票（示例）
for code in stock_list['code']:
    df = get_stock_history(code)
    signals = detect_breakout(df)
    if signals:
        print(f"股票 {code} 在以下日期出现起爆信号: {signals}")
        


# 三、策略优化与回测
# 1. 回测框架（基于Backtrader）

import backtrader as bt  

class BreakoutStrategy(bt.Strategy):  
    params = (('ma_period', 60), ('vol_multiplier', 3))  

    def __init__(self):  
        self.ma60 = bt.indicators.SMA(self.data.close, period=self.p.ma_period)  
        self.vol_ma5 = bt.indicators.SMA(self.data.volume, period=5)  

    def next(self):  
        # 起爆信号条件  
        if (self.data.volume[0] > self.vol_ma5[0] * self.p.vol_multiplier) and \  
           (self.data.close[0] > self.ma60[0]) and \  
           (self.data.close[0] > self.data.high[-1]):  # 突破前高  
            self.buy(size=1000)  
        # 止损条件：跌破5日均线  
        if self.data.close[0] < bt.indicators.SMA(self.data.close, period=5)[0]:  
            self.sell(size=1000)  

# 回测执行  
cerebro = bt.Cerebro()  
data = bt.feeds.PandasData(dataname=df_600519.set_index('date'))  
cerebro.adddata(data)  
cerebro.addstrategy(BreakoutStrategy)  
cerebro.run()  
cerebro.plot()  
        

# 五、实战案例与参数调优
# 突破60日均线时成交量放大至5倍（量比=5.2）。
# MACD金叉后红柱持续扩大，换手率连续3日>10%。
# 收益表现：信号出现后10日内涨幅达35%。
# 2. 参数调优方向
# 动态阈值：根据市场波动率调整成交量倍数（如牛市用3倍，熊市用2倍）。
# 多因子融合：加入资金流向（大单净流入占比>20%）与筹码集中度（自由流通股本<50%）


















## 第二种方法监控校验系统


# 1. 实时数据监控模块
# 功能：通过AKShare获取沪深股票实时行情，支持多股票并行监控。

import akshare as ak
import pandas as pd

# 获取全A股代码（排除ST/科创板）
stock_list = ak.stock_info_a_code_name()
stock_list = stock_list[~stock_list['code'].str.contains('ST|688')]

# 实时行情监控函数（每5秒刷新）
def realtime_monitor(codes):
    while True:
        for code in codes:
            df = ak.stock_zh_a_spot_em(symbol=code)
            # 提取关键数据：最新价、成交量、涨跌幅
            current_price = df['最新价'].iloc[0]
            volume = df['成交量'].iloc[0]
            # 调用指标计算模块
            signal = calculate_signals(code, current_price, volume)
            if signal: trigger_alert(code, signal)
        time.sleep(5)  # 控制请求频率

技术指标计算模块
策略：结合量价异动与MACD / 均线共振。

def calculate_signals(code, price, volume):
    # 获取历史数据（日线）
    hist_df = ak.stock_zh_a_daily(symbol=code, adjust="qfq")

    # 计算MACD
    hist_df['dif'] = hist_df['close'].ewm(span=12).mean() - hist_df['close'].ewm(span=26).mean()
    hist_df['dea'] = hist_df['dif'].ewm(span=9).mean()
    hist_df['macd'] = 2 * (hist_df['dif'] - hist_df['dea'])

    # 条件1：成交量突增（量比>3）
    vol_ratio = volume / hist_df['volume'].rolling(5).mean().iloc[-1]
    # 条件2：价格突破20日高点
    price_break = price > hist_df['high'].rolling(20).max().iloc[-1]
    # 条件3：MACD金叉
    macd_golden = hist_df['dif'].iloc[-1] > hist_df['dea'].iloc[-1] and hist_df['dif'].iloc[-2] < hist_df['dea'].iloc[
        -2]

    return vol_ratio > 3 and price_break and macd_golden


3. 预警与交易执行模块
实现：钉钉机器人预警 + 券商API自动下单。

# 钉钉预警（需Webhook URL）
def trigger_alert(code, signal):
    from dingtalkchatbot.chatbot import DingtalkChatbot
    webhook = "https://oapi.dingtalk.com/robot/send?access_token=xxx"
    message = f"🚨 股票 {code} 触发交易信号！\n类型：{signal}\n时间：{pd.Timestamp.now()}"
    DingtalkChatbot(webhook).send_text(msg=message)


# 模拟交易下单（以银河证券API为例）
def execute_trade(code, action, price, amount):
    if action == "BUY":
        # 调用券商买入接口（需提前开通）
        broker.buy(code, price, amount)
    elif action == "SELL":
        broker.sell(code, price, amount)


# 三、性能优化与实时性保障
# 异步并行处理
# 使用concurrent.futures实现多股票并行监控，提升响应速度。
with ThreadPoolExecutor(max_workers=10) as executor:
    executor.map(realtime_monitor, stock_chunks)

# 资源监控与告警
# 集成Jupyter资源监控扩展（如jupyterlab - system - monitor），实时检测CPU / 内存负载。
# pip install jupyterlab - system - monitor

# 设置资源阈值告警（内存 > 80 % 时暂停任务）。
# 数据缓存机制
# 使用Redis缓存历史K线数据，减少重复请求：

import redis

r = redis.Redis()
if r.exists(code):
    hist_df = pd.read_msgpack(r.get(code))
else:
    hist_df = ak.stock_zh_a_daily(code)
    r.set(code, hist_df.to_msgpack())

# 四、风险管理策略
# 交易熔断机制
# 单日最大亏损阈值（如 - 5 % 停止当日交易）。

daily_pnl = calculate_daily_profit()
if daily_pnl < -0.05:
    system_status = "STOP"

# 动态仓位控制
# 根据波动率（ATR指标）调整仓位：
atr = hist_df['high'].iloc[-1] - hist_df['low'].iloc[-1]
position_size = max(0.1, 0.02 * account_value / atr)  # 2%账户风险敞口
# 订单执行保护
# 价格滑点控制：限价单代替市价单。
# 成交失败重试机制（最多3次）。


# 五、系统部署方案
# 容器化部署
# FROM jupyter/scipy-notebook
# RUN pip install akshare dingtalkchatbot redis
# COPY trading_system.ipynb /home/jovyan/work/

# 定时任务调度
# 通过cron每日开盘前自动启动：
# 0 9 * * * docker exec my_jupyter jupyter nbconvert --execute /home/jovyan/work/trading_system.ipynb



"""







