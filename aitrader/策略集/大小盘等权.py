import bt

from bt_algos_extend import Task, Engine
import pandas as pd

def ranking_ETFs():
    t = Task()
    t.name = '大小盘等权'
    # 排序
    t.period = 'RunDaily'
    t.weight = 'WeighEqually'



    t.symbols = [
        '159915.SZ',
        '510300.SH'
        ]
    t.benchmark = '159915.SZ'
    return t

from configs import DATA_DIR_QUOTES_INDEX
res = Engine(path='quotes').run(ranking_ETFs())
import matplotlib.pyplot as plt

print(res.stats)
print(res.get_transactions())
from matplotlib import rcParams

rcParams['font.family'] = 'SimHei'
# res.plot_weights()
#res.prices.plot()

s  = res.backtests['策略'].strategy
print(s)

rc = pd.DataFrame({x.name: x.prices for x in s.securities}).unstack()

# get security positions
positions = pd.DataFrame()
for x in s.securities:
    if x.name in positions.columns:
        positions[x.name] += x.positions
    else:
        positions[x.name] = x.positions
# trades are diff
trades = positions.diff()
# must adjust first row
trades.iloc[0] = positions.iloc[0]
# now convert to unstacked series, dropping nans along the way
trades = trades[trades != 0].unstack().dropna()

# Adjust prices for bid/offer paid if needed
