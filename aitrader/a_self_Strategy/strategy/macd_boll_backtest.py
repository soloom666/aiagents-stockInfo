import backtrader as bt
import akshare as ak
from common.logger import logger
from aitrader.a_self_Strategy.untils.stocks_Info import Stock_Info
import pandas as pd

class MACDBollStrategy(bt.Strategy):
    params = dict(
        fast_period=12,
        slow_period=26,
        signal_period=9,
        boll_period=20,
        dev_factor=2.0
    )

    def __init__(self):
        # 计算MACD
        self.macd = bt.indicators.MACD(self.data.close,
                                      period_me1=self.p.fast_period,
                                      period_me2=self.p.slow_period,
                                      period_signal=self.p.signal_period)
        # 计算布林带
        self.boll = bt.indicators.BollingerBands(self.data.close,
                                                period=self.p.boll_period,
                                                devfactor=self.p.dev_factor)
        
        # 定义条件
        self.macd_golden_cross = bt.indicators.CrossOver(self.macd.macd, self.macd.signal)
        self.price_above_middle = self.data.close > self.boll.mid
        self.middle_up_trend = self.boll.mid > self.boll.mid(-1)
        
    def next(self):
        # 综合买入条件
        if not self.position:
            if (self.macd_golden_cross[0] > 0 and
                self.price_above_middle[0] and
                self.middle_up_trend[0]):
                
                # 计算仓位：资金的90%
                size = int((self.broker.getcash() * 0.9) / self.data.close[0])
                self.buy(size=size)
                logger.info(f"{self.data._name} 买入信号: {self.data.datetime.date(0)} @ {self.data.close[0]:.2f}")

    def stop(self):
        # 策略结束时记录最终资产
        logger.info(f"策略结束 {self.data._name} 最终资产: {self.broker.getvalue():.2f}")


if __name__ == '__main__':
    # 测试策略
    cerebro = bt.Cerebro()

    stock_code = '603215'
    # 获取历史数据 - 使用 baostock 替代 akshare
    df = Stock_Info.get_stock_hist_data(symbol=stock_code, start_date='20250101', end_date='20250901', period="daily", adjust="")
    if df.empty:
        logger.error(f"获取股票{stock_code}的历史数据为空")
        raise ValueError(f"获取股票{stock_code}的历史数据为空")
    # 确保日期列是datetime类型
    df['日期'] = pd.to_datetime(df['日期'])
    data = bt.feeds.PandasData(dataname=df, datetime='日期', open='开盘', high='最高',
                                  low='最低', close='收盘', volume='成交量')
    cerebro.adddata(data)


    # 设置初始资金
    cerebro.broker.setcash(100000.0)
    cerebro.broker.setcommission(commission=0.0001)  # 万1佣金

    # 添加策略和分析器
    cerebro.addstrategy(MACDBollStrategy)
    sharpe_analyzer: bt.analyzers.SharpeRatio = cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
    drawdown_analyzer: bt.analyzers.DrawDown = cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    returns_analyzer: bt.analyzers.Returns = cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
            
    # 运行回测
    results = cerebro.run()
    strat = results[0]

    # 输出分析结果
    analysis = strat.analyzers.sharpe.get_analysis()
    sharpe = analysis.get('sharperatio', 0.0)  # 使用字典安全访问
    
    returns_analysis = strat.analyzers.returns.get_analysis()
    returns = returns_analysis.get('rtot', 0.0)  # 使用正确键名并提供默认值
    
    drawdown_analysis = strat.analyzers.drawdown.get_analysis()
    drawdown = drawdown_analysis.get('max', {}).get('drawdown', 0.0)  # 嵌套值安全访问
    
    logger.info(f"{stock_code} 回测结果 - 夏普比率: {sharpe}")
    logger.info(f"收益率: {returns}")
    logger.info(f"最大回撤: {drawdown}%")

    # 绘制回测结果
    cerebro.plot()

