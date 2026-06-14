from bt_algos_extend import Task, Engine


def ranking_ETFs():
    t = Task()
    t.name = '均线能量行业轮动'
    # 排序
    t.period = 'RunDaily'
    t.weight = 'WeighEqually'
    t.select_buy = ['ma_energy(close,20)>0']
    t.select_sell = ['ma_energy(close,20)<0']
    t.order_by_topK = 2
    t.order_by_signal = 'ma_energy(close,20)'
    t.order_by_signal = 'ts_median(ts_rank(low, 20), 10)'

    t.symbols = [
        '002249.SZ',  # '512880.SH',  # 证券ETF
        '603501.SH',  # '512480.SH',  # 半导体ETF
        # '399976.SZ',  # '515030.SH',  # 新能车
        # '930697.CSI',  # '159996.SZ',  # 家电ETF
        # '399989.SZ',  # '512170.SH',  # 医药ETF
        # '000922.SH'  # '515080.SH',  # 中证红利
    ]
    t.benchmark = '000300.SH'
    return t

from configs import DATA_DIR_QUOTES_INDEX
res = Engine(path='quotes_index').run(ranking_ETFs())
import matplotlib.pyplot as plt

print(res.stats)
from matplotlib import rcParams

rcParams['font.family'] = 'SimHei'
# res.plot_weights()
res.prices.plot()
plt.show()
