from bt_algos_extend import Task, Engine


def ranking_ETFs():
    t = Task()
    t.name = '基于ETF历史评分的轮动策略'
    # 排序
    t.period = 'RunDaily'
    t.weight = 'WeighEqually'
    t.order_by_signal = 'trend_score(close,25)'
    t.start_date = '20180101'
    # t.end_date = '20240501'

    t.symbols = [
        '518880.SH',  # 黄金ETF（大宗商品）
        '513100.SH',  # 纳指100（海外资产）
        '159915.SZ',  # 创业板100（成长股，科技股，中小盘）
        '510180.SH',  # 上证180
    ]
    t.benchmark = '510300.SH'
    return t


def ranking_ETFs_risk_control():
    t = Task()
    t.name = '基于ETF历史评分的轮动策略-带止损风控'
    # 排序
    t.period = 'RunDaily'
    t.weight = 'WeighEqually'
    t.order_by_signal = 'trend_score(close,25)'
    t.select_buy = ['close>ma(close,4)']  # 入场条件
    t.select_sell = ['(1-close/shift(close,1))>0.04']  # 止损条件
    t.start_date = '20180101'
    # t.end_date = '20240501'

    t.symbols = [
        '518880.SH',  # 黄金ETF（大宗商品）
        '513100.SH',  # 纳指100（海外资产）
        '159915.SZ',  # 创业板100（成长股，科技股，中小盘）
        '510180.SH',  # 上证180（价值股，蓝筹股，中大盘）
    ]
    t.benchmark = '510300.SH'
    return t


res = Engine().run_tasks([ranking_ETFs(), ranking_ETFs_risk_control()])
import matplotlib.pyplot as plt

print(res.stats)
from matplotlib import rcParams

rcParams['font.family'] = 'SimHei'
# res.plot_weights()
(res.prices.pct_change() + 1).cumprod().plot()
plt.show()
