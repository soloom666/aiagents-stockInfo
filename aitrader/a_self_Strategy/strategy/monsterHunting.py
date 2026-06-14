import time
import random
import asyncio
import platform
import akshare as ak
import pandas as pd
# from common.logger import logger
# from common.stockBasic import sh_or_sz
from a_self_Strategy.untils.stocks_Info import Stock_Info
from common.logger import logger
import backtrader as bt
from backtrader import Cerebro, Strategy, feeds
from a_self_Strategy.strategy.yaogu_backtest import YaoguStrategy

"""
捉妖是普通2倍
普通
1、大额资金> 流通市值0.1%
2、涨幅>1%
3、半年内最高价>当前价
4、量比>1
5、外盘>内盘
"""



# 修复 Windows 下 aiodns 报错问题
if platform.system() == "Windows":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


# 1. 获取实时行情数据（含外盘/内盘/量比/流通市值）
def get_stock_data(stockType, riseRate=1):
    #普通riseRate是1， 妖股riseRate是2
    df = Stock_Info.get_stocks_All_info(stockType=stockType,riseRate=riseRate)
    # print(f"stock_zh_a_spot_em 获取实时行情可用列：{df['流通市值']}")
    # 字段重命名（以实际返回字段名为准）
    df = df.rename(columns={
        "代码": "symbol",
        "名称": "name",
        "最新价": "price",
        "涨跌幅": "price_fluctuation_range",
        "涨速": "growth_rate",
        "量比": "volume_ratio",
        "流通市值": "circ_mv"
    })
    return df[["symbol", "name", "price", "price_fluctuation_range", "growth_rate", "volume_ratio",
               "circ_mv"]]


def get_stockList_data(stock_list='', stockType='myStock',  riseRate=1):
    #普通riseRate是1， 妖股riseRate是2
    df = Stock_Info.get_stocks_All_info(stockType=stockType, stockList=stock_list, riseRate=riseRate)
    # print(f"stock_zh_a_spot_em 获取实时行情可用列：{df['流通市值']}")
    # 字段重命名（以实际返回字段名为准）
    df = df.rename(columns={
        "代码": "symbol",
        "名称": "name",
        "最新价": "price",
        "涨跌幅": "price_fluctuation_range",
        "涨速": "growth_rate",
        "量比": "volume_ratio",
        "流通市值": "circ_mv"
    })
    return df[["symbol", "name", "price", "price_fluctuation_range", "growth_rate", "volume_ratio",
               "circ_mv"]]



# 5.平台综合筛选逻辑
def common_strategy_screening(stock_list, riseRate):
    # 获取基础数据
    # realtime_df = get_stock_data(stockType=stockType, riseRate=riseRate)
    realtime_df = get_stockList_data(stock_list=stock_list, riseRate=riseRate)
    # 格式转换
    filtered = realtime_df.copy()
    # 添加动态计算字段
    filtered["fund_flow_ratio"] = 0.0
    filtered["max_6m"] = 0.0
    filtered["domestic_vol"] = 0.0
    filtered["foreign_vol"] = 0.0

    # 循环处理每只股票
    for idx, row in filtered.iterrows():
        try:
            symbol = row["symbol"]
            price_fluctuation_range = row["price_fluctuation_range"]
            growth_rate = row["growth_rate"]
            time.sleep(random.uniform(0, 1))
            # 计算主力资金比例
            fund_flow = Stock_Info.get_fund_flow(symbol)
            # print(f"{symbol} 主力资金净流入: {fund_flow}, 流动市值: {row['circ_mv']}")
            fund_ratio =  round(fund_flow / (row["circ_mv"]), 4)  # 流通市值单位亿转换为元，保留4位小数
            # print(f"{symbol} 主力资金净流入/流动市值比: {fund_ratio}")
            filtered.loc[idx, "fund_flow_ratio"] = fund_ratio

            # 计算180天历史最高价
            # time.sleep(random.uniform(0, 1))
            # max_price = Stock_Info.get_historical_high(symbol,  days=180)
            # filtered.loc[idx, "max_6m"] = max_price

            # 添加内/外盘
            time.sleep(random.uniform(0, 1))
            domestic, foreign = Stock_Info.domestic_foreign_volumn(symbol)
            filtered.loc[idx, "domestic_vol"] = domestic
            filtered.loc[idx, "foreign_vol"] = foreign
            print(f"{symbol} 主力资金净流入比: {fund_ratio}, price_fluctuation_range:{price_fluctuation_range},  growth_rate:{growth_rate},domestic: {domestic}, foreign: {foreign}")
        except Exception as e:
            print(f"获取 {symbol} 数据失败: {str(e)}")
            continue

    # 最终筛选条件:  主力资金净流入>流动市值0.1%/  外盘>内盘
    final_result = filtered[
        (filtered["fund_flow_ratio"] > 0.001 * riseRate)  # 0.1%阈值
        # & (filtered["max_6m"] > filtered["price"])
        # & (filtered["foreign_vol"] > filtered["domestic_vol"])
        ]
    monsterStocks = final_result['symbol'].tolist()
    logger.info(f"monsterStocks-妖股最终筛选结果：{monsterStocks}")

    return monsterStocks





# 6. 策略回测
def common_strategy_backtest(stock_list, start_date, end_date, riseRate=2):
    # 获取基础数据
    realtime_df = get_stockList_data(stock_list=stock_list, riseRate=riseRate)

    # 格式转换
    filtered = realtime_df.copy()

    # 添加动态计算字段
    filtered["fund_flow_ratio"] = 0.0
    filtered["max_6m"] = 0.0
    filtered["domestic_vol"] = 0.0
    filtered["foreign_vol"] = 0.0

    # 循环处理每只股票
    for idx, row in filtered.iterrows():
        try:
            symbol = row["symbol"]
            price_fluctuation_range = row["price_fluctuation_range"]
            growth_rate = row["growth_rate"]
            time.sleep(random.uniform(0, 1))
            # 计算主力资金比例
            fund_flow = Stock_Info.get_fund_flow(symbol)
            # print(f"{symbol} 主力资金净流入: {fund_flow}, 流动市值: {row['circ_mv']}")
            fund_ratio = round(fund_flow / (row["circ_mv"]), 4)  # 流通市值单位亿转换为元，保留4位小数
            # print(f"{symbol} 主力资金净流入/流动市值比: {fund_ratio}")
            filtered.loc[idx, "fund_flow_ratio"] = fund_ratio

            # 计算180天历史最高价
            # time.sleep(random.uniform(0, 1))
            # max_price = Stock_Info.get_historical_high(symbol,  days=180)
            # filtered.loc[idx, "max_6m"] = max_price

            # 添加内/外盘
            time.sleep(random.uniform(0, 1))
            domestic, foreign = Stock_Info.domestic_foreign_volumn(symbol)
            filtered.loc[idx, "domestic_vol"] = domestic
            filtered.loc[idx, "foreign_vol"] = foreign
            print(
                f"{symbol} 主力资金净流入比: {fund_ratio}, price_fluctuation_range:{price_fluctuation_range},  growth_rate:{growth_rate},domestic: {domestic}, foreign: {foreign}")
        except Exception as e:
            print(f"获取 {symbol} 数据失败: {str(e)}")
            continue

    # 最终筛选条件:  主力资金净流入>流动市值0.1%/  外盘>内盘
    final_result = filtered[
        (filtered["fund_flow_ratio"] > 0.001 * riseRate)  # 0.1%阈值
        # & (filtered["max_6m"] > filtered["price"])
        # & (filtered["foreign_vol"] > filtered["domestic_vol"])
    ]
    print(f"最终筛选结果：{final_result}")
    monsterStocks = final_result['symbol'].tolist()
    logger.info(f"monsterStocks-回测妖股最终筛选结果：{monsterStocks}")

    # 新增实时回测模块
    backtest_results = []
    for stock_code in final_result['symbol'].tolist():
        try:
            # 运行回测
            cerebro = bt.Cerebro()

            # 获取历史数据 - 使用 baostock 替代 akshare
            try:
                df = Stock_Info.get_stock_hist_data(symbol=stock_code, start_date=start_date, end_date=end_date,
                                        period="daily", adjust="")
                if df.empty:
                    logger.error(f"获取股票{stock_code}的历史数据为空")
                    return None

                # 确保日期列是datetime类型
                df['日期'] = pd.to_datetime(df['日期'])

                # 数据转换为backtrader需要的格式
                data = feeds.PandasData(dataname=df, datetime='日期', open='开盘', high='最高', low='最低',
                                        close='收盘', volume='成交量')
                cerebro.adddata(data)
            except Exception as e:
                logger.error(f"加载历史数据失败: {str(e)}")
                return None

            # 设置初始资金
            cerebro.broker.setcash(100000.0)

            # 添加策略和分析器
            cerebro.addstrategy(YaoguStrategy, stock_code=stock_code)
            cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
            cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
            cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')

            # 运行回测
            results = cerebro.run()
            strat = results[0]

            # 收集分析结果
            sharpe = strat.analyzers.sharpe.get_analysis().sharperatio if hasattr(strat.analyzers.sharpe.get_analysis(),
                                                                                  'sharperatio') else 0.0
            returns = strat.analyzers.returns.get_analysis().total if hasattr(strat.analyzers.returns.get_analysis(),
                                                                              'total') else 0.0
            drawdown = strat.analyzers.drawdown.get_analysis().max.drawdown if hasattr(
                strat.analyzers.drawdown.get_analysis(), 'max') and hasattr(strat.analyzers.drawdown.get_analysis().max,
                                                                            'drawdown') else 0.0

            backtest_results.append({
                'symbol': stock_code,
                'sharpe': sharpe,
                'returns': returns,
                'drawdown': drawdown
            })

            logger.info(f"{stock_code} 回测结果 - 夏普比率: {sharpe:.2f}, 收益率: {returns:.2%}")

        except Exception as e:
            logger.error(f"{stock_code} 回测失败: {str(e)}")
            continue

    # 最终返回包含回测结果的增强型列表
    enhanced_list = [{
        'stock_code': item['symbol'],
        'sharpe_ratio': item['sharpe'] if item['sharpe'] is not None else 0.0,
        'total_return': item['returns'] if item['returns'] is not None else 0.0,
        'max_drawdown': item['drawdown'] if item['drawdown'] is not None else 0.0
    } for item in backtest_results]

    logger.info(f"回测增强型妖股列表: {enhanced_list}")

    # 输出图表
    cerebro.plot()

    return enhanced_list











if __name__ == '__main__':
    # common_strategy_screening(stockType='myStock', riseRate=2)
    # get_stock_data(stockType='myStock', riseRate=2)
    get_stock_data(stockType='myStock', riseRate=2)
    # print(get_stockList_data(stockList=['002249','603215'],stockType='myStock'))
    # common_strategy_backtest(stockCode=['603215'],start_date='20250101',end_date='20250731')
    # Stock_Info.get_stocks_All_info(stockList='603215', stockType='myStock')