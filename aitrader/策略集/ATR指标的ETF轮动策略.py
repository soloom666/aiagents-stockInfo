from bt_algos_extend import Task, Engine


def ranking_ETFs():
    t = Task()
    t.name = '均线能量行业轮动'
    # 排序
    t.period = 'RunDaily'
    t.weight = 'WeighEqually'
    t.order_by_signal = 'ATR(high,low,close,10)/close'
    t.start_date = '20210101'

    t.symbols = [
        '162411.SZ',  # 华宝油气LOF'
        '159981.SZ',  # 能源化工
        '159980.SZ',  # 有色
        '518880.SH',  # 黄金
        '161226.SZ',  # 白银
        '159985.SZ',  # 豆粕
        # 跨境
        '164824.SZ',  # 印度
        '159920.SZ',  # 恒生
        '513100.SH',  # 纳指
        '513080.SH',  # 法国CAC40
        '513030.SH',  # 德国30
        '513520.SH',  # 日经
    ]
    t.benchmark = '510300.SH'
    return t


from configs import DATA_DIR_QUOTES_INDEX

res = Engine(path='quotes').run(ranking_ETFs())
import matplotlib.pyplot as plt

print(res.stats)
from matplotlib import rcParams

rcParams['font.family'] = 'SimHei'
# res.plot_weights()
(res.prices.pct_change()+1).cumprod().plot()
plt.show()
