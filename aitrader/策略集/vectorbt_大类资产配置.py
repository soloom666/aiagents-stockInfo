import vectorbt as vbt
import pandas as pd

from datafeed.dataloader import CSVDataloader

etf_tickers = {
    '000300.SH': '中证300',
    '399006.SZ': '中证500',
}
data = CSVDataloader.get(['603501.SH', '002249.SZ'], path='quotes_index')
prices = data
prices.dropna(inplace=True)

import numpy as np
import pandas as pd
import vectorbt as vbt
import yfinance as yf

# 1. 参数设置
assets = ['000300.SH', '399006.SZ']  # 示例资产（美股、美债、黄金、国债）
start_date = '2020-01-01'
end_date = '2025-04-31'
# rebalance_freq = 'Q'  # 季度调仓
rebalance_freq = 'QE'

# 2. 获取数据
#prices = yf.download(assets, start=start_date, end=end_date)['Adj Close']
prices = prices.asfreq('D').ffill()  # 填充非交易日

# 3. 生成调仓信号
# 获取季度首日交易日日期
rebalance_dates = prices.resample(rebalance_freq).first().dropna().index

# 创建信号矩阵（1表示调仓日）
signal_df = pd.DataFrame(0, index=prices.index, columns=prices.columns)
signal_df.loc[rebalance_dates] = 1


# 4. 创建投资组合
def rebalance_weights(close, fees=0.001):
    # 计算等权重（1/N）
    weights = close.vbt.signals.fshift().apply(
        lambda x: pd.Series([1 / len(assets)] * len(assets),
                            index=assets) if x else None,
        axis=1
    ).ffill()

    # 生成订单（百分比目标权重）
    return weights.vbt.portfolio.from_orders(
        close=close,
        size=weights,
        size_type='targetpercent',
        fees=fees,
        init_cash=100000,
        freq='D'
    )


# 5. 运行回测
pf = rebalance_weights(prices, fees=0.001)

# 6. 结果分析
print("===== 策略表现 =====")
print(pf.stats())

# 可视化
pf.plot().show()
pf.plot_weights().show()

# 输出每次调仓记录
print("\n===== 调仓记录 =====")
print(pf.orders.records_readable)
