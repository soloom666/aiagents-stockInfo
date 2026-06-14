import bt
from bt_algos_extend import Task, Engine


def risk_parity_hongli_ndx():
    t = Task()
    t.name = '大类资产配置-风险平价系列-等权重-红利低波-纳指'
    # 排序
    t.start_date = '20200101'
    t.period = 'RunMonthly'  # 月底调仓
    t.weight = 'WeighEqually'

    t.symbols = [
        '159934.SZ',  # 黄金ETF（黄金）
        '511260.SH',  # 十年国债ETF（债券）
        '512890.SH',  # 红利低波（股票）
        '159985.SZ',  # 豆粕（商品）
        '513100.SH'  # 纳指100
    ]
    t.benchmark = '510300.SH'
    return t


def astock_rolling():
    t = Task()
    t.name = '大小盘轮动'
    # 排序
    t.start_date = '20200101'
    # t.period = 'RunMonthly'  # 月底调仓
    t.weight = 'WeighEqually'

    t.symbols = [
        '159915.SZ'  # 创业板
    ]
    t.benchmark = '512890.SH'
    t.select_buy = ['roc(close,20)>0.08']
    t.select_sell = ['roc(close,20)<0']
    t.order_by_signal = 'roc(close,20)'
    return t

symbols = [
    '159934.SZ',  # 黄金ETF（黄金）
    # '511260.SH',  # 十年国债ETF（债券）
    # '161716.SZ',
    # '512890.SH',  # 红利低波（股票）
    '159985.SZ',  # 豆粕（商品）
    '513100.SH'  # 纳指100
]

from bt_algos_extend import MultiStrategies
s = MultiStrategies()

s.weight= 'WeighInvVol'
s.id_or_symbols = [*symbols,'1111111fdfdfdfdfd111111']
res = Engine().run_multi_tasks(s)
import matplotlib.pyplot as plt
print(res.stats)
from matplotlib import rcParams

rcParams['font.family'] = 'SimHei'
res.plot_weights()
res.prices.plot()
plt.show()

