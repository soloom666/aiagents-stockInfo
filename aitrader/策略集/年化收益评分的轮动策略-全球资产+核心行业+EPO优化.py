from bt_algos_extend import Task, Engine


def ranking_ETFs():
    t = Task()
    t.name = '基于ETF历史评分的轮动策略'
    # 排序
    t.period = 'RunDaily'
    t.weight = 'WeighEqually'
    t.order_by_signal = 'trend_score(close,25)'
    t.start_date = '20180101'
    t.order_by_topK = 1
    # t.end_date = '20240501'

    t.symbols = [
        '518880.SH',  # 黄金ETF
        '513100.SH',  # 纳指ETF
        '159985.SZ',  # 豆粕ETF
        '159919.SZ',  # 沪深300ETF
        '159992.SZ',  # 创新药ETF
        '560080.SH',  # 中药ETF
        '515700.SH',  # 新能车ETF
        '515790.SH',  # 光伏ETF
        '515880.SH',  # 通信ETF
        '512720.SH',  # 计算机ETF
        '159740.SZ',  # 恒生科技ETF
    ]
    t.benchmark = '510300.SH'
    return t


res = Engine().run(ranking_ETFs())
import matplotlib.pyplot as plt

print(res.stats)
from matplotlib import rcParams

rcParams['font.family'] = 'SimHei'
# res.plot_weights()
(res.prices.pct_change() + 1).cumprod().plot()
plt.show()
