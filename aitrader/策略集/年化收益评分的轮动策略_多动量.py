from bt_algos_extend import Task, Engine


def ranking_ETFs():
    t = Task()
    t.name = '基于ETF历史评分的轮动策略'
    # 排序
    t.period = 'RunDaily'
    t.weight = 'WeighEqually'
    t.order_by_signal = 'trend_score(close,25)*0.4+(roc(close,5)+roc(close,10))*0.2+ma(volume,5)/ma(volume,20)'
    # t.start_date = '20180101'
    # t.end_date = '20240501'

    t.symbols = [
        '159915.SZ',  # '创业板ETF',
        '510180.SH',  # '上证180ETF',
        '518880.SH',  # '黄金ETF',
        '513100.SH',  # '纳指ETF',
        '159509.SZ',  # '纳指科技ETF',
        '512100.SH',  # '中证1000ETF',
        '513500.SH',  # '标普500ETF',
        '512480.SH',  # '科创100ETF'
    ]
    t.benchmark = '510300.SH'
    return t


res = Engine().run(ranking_ETFs())
import matplotlib.pyplot as plt

print(res.stats)
from matplotlib import rcParams

rcParams['font.family'] = 'SimHei'
# res.plot_weights()
res.prices.plot()
print(res.get_transactions())
df = (res.prices.pct_change() + 1).cumprod()
print(df.iloc[-1])
plt.show()
