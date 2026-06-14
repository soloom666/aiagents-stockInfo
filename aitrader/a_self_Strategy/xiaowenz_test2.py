import numpy as np
import pandas as pd
import math
from kuanke.user_space_api import *
from jqlib.technical_analysis import *
from jqdata import *

# 初始化函数 - 策略配置和参数设置
def initialize(context):
    """
    策略初始化函数，设置交易环境、参数和定时任务
    """
    # 设定基准 - 以沪深300指数作为业绩比较基准
    set_benchmark('000300.XSHG')
    # 用真实价格交易 - 避免使用复权价格，更贴近实盘
    set_option('use_real_price', True)
    # 打开防未来函数 - 防止使用未来数据，确保策略可实盘
    set_option("avoid_future_data", True)
    # 设置滑点 - 固定滑点0.1%，模拟实际交易中的价格冲击
    set_slippage(FixedSlippage(0.003))
    # 设置交易成本 - ETF交易成本较低，符合实际交易情况
    set_order_cost(OrderCost(open_tax=0, close_tax=0, open_commission=0.0002, close_commission=0.0002, close_today_commission=0, min_commission=5), type='fund')
    # 过滤一定级别的日志 - 只显示错误日志，减少日志干扰
    log.set_level('system', 'error')

    # 策略参数配置
    g.etf_pool = [
        '518880.XSHG',  # 黄金ETF - 大宗商品类资产，抗通胀避险
        '513100.XSHG',  # 纳指100ETF - 海外科技股，分散A股风险
        '159915.XSHE',  # 创业板ETF - 成长股代表，高弹性
        '588200.XSHG',  # 科创芯片
        '561160.XSHG',  # 新能源
        '515880.XSHG',  # 通信
        '159828.XSHE',  # 医疗
        '161725.XSHE',   # 白酒
        '560860.XSHG',
        "563230.XSHG"
    ]
    
    g.m_days = 25  # 动量参考天数 - 约1个月交易日的动量周期
    g.strategy ='smallETF'  # 策略标识名
    g.n = 25  # 均线参数，默认值为5

    # 定时任务设置
    run_daily(trade, time='09:55')  # 每天09:55执行交易


def MOM(etf):
    """
    动量因子计算函数 - 基于加权线性回归的动量评分
    核心思想：近期价格变化比远期价格变化更重要

    计算步骤：
    1. 获取历史价格数据
    2. 对价格取对数，转换为线性关系
    3. 使用加权线性回归拟合价格趋势
    4. 计算年化收益率和R²判定系数
    5. 综合评分 = 年化收益率 × R²

    参数：
    etf: ETF代码

    返回：
    score: 动量综合评分
    """
    # 获取25个交易日的收盘价数据
    df = attribute_history(etf, g.m_days, '1d', ['close'])
    # 对价格取对数，使价格变化更符合线性关系
    y = np.log(df['close'].values)
    n = len(y)
    x = np.arange(n)  # 时间序列 [0, 1, 2,..., n - 1]

    # 权重设置：近期数据权重更高（1 - 2线性递增）
    weights = np.linspace(1, 2, n)  # 线性增加权重，最近数据权重为2

    # 加权线性回归拟合价格趋势
    slope, intercept = np.polyfit(x, y, 1, w=weights)

    # 计算年化收益率：将日收益率转换为年化收益率
    annualized_returns = math.pow(math.exp(slope), 250) - 1

    # 计算R²判定系数，衡量趋势的稳定性
    residuals = y - (slope * x + intercept)  # 残差
    weighted_residuals = weights * residuals ** 2  # 加权残差平方和
    r_squared = 1 - (np.sum(weighted_residuals) / np.sum(weights * (y - np.mean(y)) ** 2))

    # 综合评分：收益率 × 趋势稳定性
    score = annualized_returns * r_squared
    return score


def get_rank(etf_pool,previous_date):
    """
    ETF动量排名函数 - 基于动量评分对ETF进行排序和筛选
    核心功能：计算所有ETF的动量评分，按得分排序，并应用安全区间过滤

    风险控制逻辑：
    - 得分>0：确保有正向动量
    - 得分<=5：避免动量过高（可能意味着泡沫或过度投机）
    - 如果所有ETF得分都不在安全区间，则空仓避险

    参数：
    etf_pool: ETF代码列表

    返回：
    rank_list: 符合条件的ETF排名列表（按动量从高到低）
    """
    eligible_etf_pool = []
    for etf in etf_pool:
        EMA144 = EMA(etf, previous_date, timeperiod=144, unit='1d', include_now=True, fq_ref_date=None)[etf]
        EMA576 = EMA(etf, previous_date, timeperiod=576, unit='1d', include_now=True, fq_ref_date=None)[etf]
        if EMA144 >= EMA576:
            eligible_etf_pool.append(etf)
            
    score_list = []
    # 计算每个ETF的动量评分
    for etf in eligible_etf_pool:
        score = MOM(etf)
        score_list.append(score)

    # 创建DataFrame并排序
    df = pd.DataFrame(index=eligible_etf_pool, data={'score': score_list})
    df = df.sort_values(by='score', ascending=False)  # 按得分降序排列

    # 安全区间过滤：得分在(0, 5]范围内
    # 得分>0：确保正向动量，避免负向趋势
    # 得分<=5：避免动量过高，防止追高风险
    df = df[(df['score'] > 0) & (df['score'] <= 10)]

    rank_list = list(df.index)

    # 风险控制：如果所有ETF都不符合条件，则空仓避险
    if len(rank_list) == 0:
        rank_list = []  # 空仓，等待更好的入场时机

    return rank_list


def trade(context):
    """
    交易执行函数 - 每天执行的交易逻辑
    核心策略：卖出非目标ETF，买入动量最强的ETF

    交易流程：
    1. 获取动量排名最高的ETF
    2. 卖出当前持仓中不在目标列表的ETF
    3. 买入目标ETF（如果当前未持有且价格在n日线上方）
    4. 卖出目标ETF（如果当前持有且价格在n日线下方）

    风险控制：
    - 只持有1只ETF，集中投资于最强动量
    - 如果所有ETF都不符合条件，则空仓避险
    """
    log.info("每天09:55执行交易")

    # 策略配置：每次只持有1只动量最强的ETF
    target_num = 2
    EMA144 = EMA('000001.XSHG', context.previous_date.strftime('%Y-%m-%d'), timeperiod=144, unit='1d', include_now=True, fq_ref_date=None)['000001.XSHG']
    EMA576 = EMA('000001.XSHG', context.previous_date.strftime('%Y-%m-%d'), timeperiod=576, unit='1d', include_now=True, fq_ref_date=None)['000001.XSHG']
    if EMA144 < EMA576:
        target_num = 1
    # 获取动量排名最高的ETF（最多取target_num只）
    target_list = get_rank(g.etf_pool,context.previous_date.strftime('%Y-%m-%d'))[:target_num]

    # 卖出逻辑：卖出不在目标列表中的持仓ETF
    hold_list = list(context.portfolio.positions)
    for etf in hold_list:
        if etf not in target_list:
            # 清仓卖出非目标ETF
            order_target_value(etf, 0)
            log.info('卖出' + str(etf))
        else:
            # 获取n日收盘价数据
            AMV1 = AMV(etf,check_date=context.previous_date.strftime('%Y-%m-%d'), timeperiod=g.m_days)
            current_price = get_current_data()[etf].last_price
            if current_price < AMV1[etf]:
                order_target_value(etf, 0)
                log.info('卖出' + str(etf))
            else:
                log.info('继续持有' + str(etf))

    # 买入逻辑：买入目标ETF（如果当前未持有且价格在n日线上方）
    hold_list = list(context.portfolio.positions)  # 重新获取持仓列表（卖出后可能变化）
    buy_list = []
    if len(hold_list) < target_num:

        for etf in target_list:
            # 获取n日收盘价数据
            current_price = get_current_data()[etf].last_price
            RSI10_1, RSI6_1 = MARSI(etf, check_date=context.previous_date.strftime('%Y-%m-%d'), M1=10, M2=6)
            AMV1 = AMV(etf, check_date=context.previous_date.strftime('%Y-%m-%d'), timeperiod=g.m_days)
            # 如果当前未持有该ETF且当前价格高于n日均线，则买入
            if context.portfolio.positions[etf].total_amount == 0 and current_price > AMV1[etf] and RSI10_1[etf] < 80:
                buy_list.append(etf)

    available_cash = context.portfolio.available_cash
    for etf in buy_list:
        order_target_value(etf, available_cash / len(buy_list))