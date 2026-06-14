import random
import time

import akshare as ak
import pandas as pd
from backtrader import Cerebro, Strategy, feeds
from common.getTime import getDateStr
from common.logger import logger
from a_self_Strategy.untils.stocks_Info import Stock_Info
import backtrader as bt
from common.readFile import ReadFile

confJson = ReadFile.read_json()
start_date = confJson['开始时间']
end_date = getDateStr()
init_capital = confJson['初始资金']


class YaoguStrategy(Strategy):
    """
    基于妖股起爆点分析的交易策略
    """
    params = (
        ('maperiod', 150),  # 均线周期
        ('printlog', True),  # 是否打印日志
        ('stock_code', '603215'),  # 股票代码
    )

    def log(self, txt, dt=None, doprint=False):
        """ Logging function for this strategy"""
        if self.params.printlog or doprint:
            dt = dt or self.datas[0].datetime.date(0)
            print(f'{dt.isoformat()}, {txt}')

    def __init__(self):
        # 确保正确初始化SMA指标
        self.sma_3 = bt.indicators.SimpleMovingAverage(self.datas[0], period=3)
        self.sma_10 = bt.indicators.SimpleMovingAverage(self.datas[0], period=10)
        self.sma_20 = bt.indicators.SimpleMovingAverage(self.datas[0], period=20)
        self.sma_60 = bt.indicators.SimpleMovingAverage(self.datas[0], period=60)

        # 创建MACD指标（确保在访问前初始化）
        self.macd = bt.indicators.MACD(self.datas[0],
                                     period_me1=12,
                                     period_me2=26,
                                     period_signal=9)
        
        # 在MACD初始化后添加调试信息
        print("MACD数据线属性:", dir(self.macd.lines))  # 确保在初始化后访问
        
        # 初始化其他指标...
        # 计算ATR用于动态止损
        self.atr = bt.indicators.ATR(self.datas[0], period=14)
        
        # 获取历史资金流向数据（模拟）
        self.fund_flow_data = Stock_Info.get_fund_flowInfo(symbol=self.params.stock_code, type='all')
        
        # 获取筹码分布数据（模拟）
        self.cyq_data = Stock_Info.get_cyq_data(self.params.stock_code)
        
        # 初始化交易信号权重
        self.signal_weights = {
            'volume': 1.2,   # 成交量异动权重
            'price': 1.5,    # 价格突破权重
            'macd': 1.8,     # MACD信号权重
            'cyq': 1.3,      # 筹码分布权重
            'fund_flow': 1.0 # 资金流向权重
        }
        
        # 记录最近交易日期
        self.last_trade_date = None

    def next(self):
        # 确保有足够的历史数据（根据最长周期调整，这里使用60日均线）
        if len(self.data_close) < 60:
            return
        
        # 打印均线值（调试信息）
        current_date = self.datas[0].datetime.date(0)
        sma_value3 = self.sma_3.lines.sma[0]
        sma_value10 = self.sma_10.lines.sma[0]
        sma_value20 = self.sma_20.lines.sma[0]
        sma_value60 = self.sma_60.lines.sma[0]
        logger.debug(f"{current_date} 10日均线值: {sma_value10:.2f},20日均线值: {sma_value20:.2f},60日均线值: {sma_value60:.2f}")
        
        # 避免同一天多次交易
        if self.last_trade_date == current_date:
            return
        
        # 模拟实时数据获取
        hist_data = {
            '收盘': [self.data_close[i] for i in range(-59, 1)],
            '成交量': [self.datas[0].volume[i] for i in range(-59, 1)],
            '最高': [self.datas[0].high[i] for i in range(-59, 1)],
            '最低': [self.datas[0].low[i] for i in range(-59, 1)]
        }
        
        # 交易信号评分系统
        signal_scores = {}
        
        # 1. 成交量异动条件（增加动态基准）
        avg_volume_20 = sum(hist_data['成交量'][-20:]) / 20
        volume_score = 2.0 if hist_data['成交量'][-1] > 5 * avg_volume_20 else \
                     1.5 if hist_data['成交量'][-1] > 3 * avg_volume_20 else \
                     0.5 if hist_data['成交量'][-1] > avg_volume_20 else 0
        signal_scores['volume'] = volume_score
        
        # 2. 价格突破条件（多级突破检测）
        price_break_score = 0
        if hist_data['收盘'][-1] > max(hist_data['最高'][-60:-1]):
            price_break_score = 2.0  # 创60日新高
        elif hist_data['收盘'][-1] > max(hist_data['最高'][-30:-1]):
            price_break_score = 1.5  # 创30日新高
        elif hist_data['收盘'][-1] > sma_value20:  # 站上20日均线
            price_break_score = 1.0
        signal_scores['price'] = price_break_score
        
        # 3. MACD条件（使用框架推荐的标准访问方式）
        macd_score = 0
        if self.macd.lines.macd[0] > self.macd.lines.signal[0] and \
           self.macd.lines.macd[-1] > self.macd.lines.signal[-1] and \
           self.macd.lines.macd[0] > 0:  # 连续两日金叉且在零轴上方
            try:
                # 使用属性列表替代多重判断
                histogram_attrs = ['hist', 'histgram', 'histo']
                histogram_value = None
                prev_histogram_value = None
                
                for attr in histogram_attrs:
                    if hasattr(self.macd.lines, attr):
                        try:
                            histogram_value = getattr(self.macd.lines, attr)[0]
                            prev_histogram_value = getattr(self.macd.lines, attr)[-1]
                            break
                        except (AttributeError, IndexError) as e:
                            logger.error(f"MACD柱状图访问错误({attr}): {str(e)}")
                            continue
                
                if histogram_value is not None and prev_histogram_value is not None:
                    macd_score = 2.0 if histogram_value > 2 * prev_histogram_value else 1.5
                else:
                    logger.warning("未找到可用的MACD柱状图属性")
                    macd_score = 0
            except Exception as e:
                logger.error(f"MACD柱状图访问错误(未知异常): {str(e)}")
                macd_score = 0
        signal_scores['macd'] = macd_score
        
        # 4. 筹码分布条件（优化计算逻辑）
        cyq_condition = False
        cyq_score = 0
        if not self.cyq_data.empty and len(self.cyq_data) >= 2:
            try:
                # 计算筹码峰
                avg_cost = pd.to_numeric(self.cyq_data.iloc[:, 1], errors='coerce')
                concentration_70 = pd.to_numeric(self.cyq_data.iloc[:, 3], errors='coerce')
                chip_peak = (avg_cost * concentration_70).rolling(30).sum()
                
                # 多维度筹码分布评估
                concentration_score = 2.0 if self.cyq_data['90集中度'].iloc[-1] < 15 else \
                                 1.5 if self.cyq_data['90集中度'].iloc[-1] < 20 else 0
                
                peak_score = 1.5 if chip_peak.iloc[-1] > 0.7 else \
                           1.0 if chip_peak.iloc[-1] > 0.5 else 0
                
                # 成本转移检测（筹码快速上移）
                cost_diff = (avg_cost.iloc[-1] - avg_cost.iloc[-2]) / avg_cost.iloc[-2]
                cost_shift_score = 1.0 if cost_diff > 0.03 else 0.5 if cost_diff > 0.01 else 0
                
                cyq_score = concentration_score + peak_score + cost_shift_score
            except Exception as e:
                logger.error(f"筹码分布计算错误: {str(e)}")
                cyq_score = 0
        signal_scores['cyq'] = cyq_score
        
        # 5. 大单净流入条件（增加时间衰减因子）
        fund_flow_score = 0
        if not self.fund_flow_data.empty:
            try:
                # 取最近3日资金流
                recent_flow = self.fund_flow_data.iloc[-3:]
                # 计算加权净流入比例
                for i, (_, row) in enumerate(recent_flow.iterrows()):
                    print(f"收盘价：{hist_data['收盘'][-1]}")
                    cje = hist_data['成交量'][-1] * hist_data['收盘'][-1] * 1000
                    print(f"主力流入净额：{row['主力净流入-净额']}，当天成交额: {cje}")
                    weighted_flow = sum([
                        (row['主力净流入-净额'] / cje) * (1 - i/10)

                    ])
                logger.info(f'主力净流入/成交量比 weighted_flow：{weighted_flow}')
                if weighted_flow > 0.3:
                    fund_flow_score = 2.0
                elif weighted_flow > 0.1:
                    fund_flow_score = 1.5
                elif weighted_flow > 0:
                    fund_flow_score = 0.5
            except Exception as e:
                logger.error(f"资金流向计算错误: {str(e)}")
        
        signal_scores['fund_flow'] = fund_flow_score
        
        # 计算综合信号得分
        total_score = sum(score * self.signal_weights[key] for key, score in signal_scores.items())
        signal_strength = total_score / sum(self.signal_weights.values())  # 标准化得分
        
        # 动态买卖决策
        if not self.position:
            # 买入条件：综合得分超过阈值且满足趋势过滤
            if signal_strength >= 1 and hist_data['收盘'][-1] > sma_value60:
                self.log(f'发现妖股机会！{current_date} 收盘价: {hist_data["收盘"][-1]:.2f}')
                self.log(f'信号详情: {signal_scores}, 综合得分: {signal_strength:.2f}')
                logger.info(f"买入信号！{current_date} 信号详情: {signal_scores}, 综合得分: {signal_strength:.2f}")
                # 动态仓位计算（基于ATR和账户余额）
                atr_value = self.atr[0]
                account_risk = self.broker.getvalue() * 0.02  # 单笔风险控制在2%
                size = int(account_risk / (atr_value * 2))  # 2倍ATR作为止损幅度
                
                self.buy(size=size if size > 0 else 100)  # 最小买入100股
                self.last_trade_date = current_date
        elif signal_strength < 1 and hist_data['收盘'][-1] > sma_value3:
        # else:
            # 动态止损止盈
            logger.info(f"卖出信号！{current_date} 信号详情: {signal_scores}, 综合得分: {signal_strength:.2f}")

            buy_price = 0
            try:
                # 使用标准positions属性获取持仓信息
                if self.broker.positions:  # 检查是否有持仓
                    # 获取第一个持仓的价格
                    for d, pos in self.broker.positions.items():
                        if pos.size > 0:  # 找到第一个有持仓的标的
                            buy_price = pos.price
                            break
            except Exception as e:
                logger.error(f"持仓信息获取错误: {str(e)}")
                buy_price = 0
            current_return = (hist_data['收盘'][-1] - buy_price) / buy_price

            # 动态跟踪止损（基于ATR）
            stop_loss = max(
                buy_price * 0.95,  # 最低5%止损
                buy_price - 2 * self.atr[0]  # 固定2倍ATR作为初始止损
            )
            
            # 止盈条件：跌破10日均线或出现放量滞涨
            take_profit = hist_data['收盘'][-1] < sma_value10 or \
                          (hist_data['成交量'][-1] > 2 * avg_volume_20 and current_return < 0.02)
            
            if hist_data['收盘'][-1] < stop_loss or take_profit:
                self.log(f'交易结束！{current_date} 收盘价: {hist_data["收盘"][-1]:.2f}, 收益: {current_return:.2%}')
                self.log(f'止损位: {stop_loss:.2f}, 当前ATR: {self.atr[0]:.2f}')
                self.close()
                self.last_trade_date = current_date

    def stop(self):
        # 记录结束时的账户价值
        final_value = self.broker.getvalue()
        # 计算收益率
        returns = (final_value / self.broker.startingcash) - 1
        
        self.log(f'(参数 maperiod = {self.params.maperiod}) 最终资产价值: {final_value:.2f}')
        self.log(f'(参数 maperiod = {self.params.maperiod}) 总收益率: {returns:.2%}')

def run_backtest(stock_code='000001', start_date=start_date, end_date=end_date):
    """
    运行回测
    :param stock_code: 股票代码
    :param start_date: 开始日期 (YYYYMMDD格式)
    :param end_date: 结束日期 (YYYYMMDD格式)
    :return: 回测结果
    """
    # 初始化Cerebro引擎
    cerebro = Cerebro()
    
    # 获取历史数据 - 使用 baostock 替代 akshare
    try:
        df = Stock_Info.get_stock_hist_data(symbol=stock_code, start_date=start_date, end_date=end_date, period="daily", adjust="")
        if df.empty:
            logger.error(f"获取股票{stock_code}的历史数据为空")
            return None
        
        # 确保日期列是datetime类型
        df['日期'] = pd.to_datetime(df['日期'])
        
        # 数据转换为backtrader需要的格式
        data = feeds.PandasData(dataname=df, datetime='日期', open='开盘', high='最高', low='最低', close='收盘', volume='成交量')
        cerebro.adddata(data)
    except Exception as e:
        logger.error(f"加载历史数据失败: {str(e)}")
        return None
    
    # 设置初始资金
    cerebro.broker.setcash(init_capital)
    cerebro.broker.setcommission(commission=0.0001)  # 万1佣金

    # 添加策略
    cerebro.addstrategy(YaoguStrategy, stock_code=stock_code, printlog=True)
    
    # 添加分析器
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe_ratio')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
    
    # 运行回测
    results = cerebro.run()
    
    # 获取分析结果
    strat = results[0]
    analysis = {
        'sharpe_ratio': strat.analyzers.sharpe_ratio.get_analysis(),
        'drawdown': strat.analyzers.drawdown.get_analysis(),
        'returns': strat.analyzers.returns.get_analysis()
    }
    
    # 输出图表
    # cerebro.plot()

    return analysis




if __name__ == '__main__':
    # 回测函数
    back_result_list = []
    stock_code = Stock_Info.my_stock_from_excel()
    for stock_code in stock_code:
        time.sleep(random.uniform(0, 1))
        analysis = run_backtest(stock_code)
        if analysis:
            # 使用get方法设置默认值防止KeyError
            sharpe_ratio_value = analysis['sharpe_ratio'].get('sharperatio', 0)
            total_return = analysis['returns'].get('total', 0)
            annualized_return = analysis['returns'].get('rnorm100', 0)
            max_drawdown = analysis['drawdown']['max']['drawdown']
            logger.info(f"回测结果分析 - 股票: {stock_code}, 夏普比率: {sharpe_ratio_value}")
            logger.info(f"年化收益率: {annualized_return:.2%}")
            logger.info(f"最大回撤: {max_drawdown:.2%}")
            analysis_dict = {
                "stock_code": stock_code,
                "夏普比率": sharpe_ratio_value,
                "年化收益率": annualized_return,
                "最大回撤": max_drawdown
            }
            print(f'个股分析结果：{analysis_dict}')
            back_result_list.append(analysis_dict)
    logger.info(f"回测结果列表: {back_result_list}")

    # 转换为DataFrame
    df = pd.DataFrame(back_result_list)
    # 年化收益率前10（倒序）
    top_annualized = df.sort_values(by='年化收益率', ascending=False).head(10)[['stock_code', '年化收益率','夏普比率', '最大回撤']]
    print("年化收益率前10:\n", top_annualized)

    # 夏普比率前10（倒序）
    # top_sharpe = df.sort_values(by='夏普比率', ascending=False).head(10)[['stock_code', '年化收益率','夏普比率', '最大回撤']]
    # print("\n夏普比率前10:\n", top_sharpe)