from dataclasses import dataclass, asdict
from typing import List, Dict

import bt
import numpy as np
import pandas as pd
from bt import Algo


class WeighEPO(Algo):
    """
    内置锚定向量的EPO权重分配算子

    Args:
        * anchor_method (str): 锚定向量生成方法
            - 'equal' : 等权重 (默认)
            - 'vol'   : 波动率倒数权重
            - 'mean'  : 历史收益率均值权重
            - 'rvrp'  : 风险平价权重
        * anchor_lookback (DateOffset): 锚定向量计算窗口
        * other原有参数保持不变...
    """

    def __init__(self, lambda_=1.0, method="simple", w=0.5,
                 anchor_method='equal', anchor_lookback=None,
                 normalize=True, endogenous=True,
                 lookback=pd.DateOffset(months=3), lag=pd.DateOffset(days=0)):
        super(WeighEPO, self).__init__()

        # 参数验证
        valid_anchor_methods = ['equal', 'vol', 'mean', 'rvrp']
        if anchor_method not in valid_anchor_methods:
            raise ValueError(f"Anchor method must be in {valid_anchor_methods}")

        self.lambda_ = lambda_
        self.method = method
        self.w = w
        self.anchor_method = anchor_method
        self.anchor_lookback = anchor_lookback or lookback  # 默认使用主lookback
        self.normalize = normalize
        self.endogenous = endogenous
        self.lookback = lookback
        self.lag = lag

    def _get_anchor_data(self, target, selected):
        """获取锚定向量计算所需数据"""
        t0 = target.now - self.lag
        start = t0 - self.anchor_lookback
        prices = target.universe.loc[start:t0, selected]
        return prices.to_returns().dropna()

    def _generate_anchor(self, target, selected):
        """核心锚定向量生成逻辑"""
        if len(selected) == 0:
            return pd.Series()

        # 等权重
        if self.anchor_method == 'equal':
            n = len(selected)
            return pd.Series(1 / n, index=selected)

        # 需要收益数据的方法
        returns = self._get_anchor_data(target, selected)

        # 波动率倒数权重
        if self.anchor_method == 'vol':
            vol = returns.std()
            inv_vol = 1 / vol.replace(0, 1e-6)  # 防止除零
            return inv_vol / inv_vol.sum()

        # 收益率均值权重
        if self.anchor_method == 'mean':
            mean_ret = returns.mean()
            return mean_ret / mean_ret.abs().sum()

        # 风险平价权重
        if self.anchor_method == 'rvrp':
            cov = returns.cov()
            try:
                return pd.Series(bt.ffn.calc_risk_parity_weights(cov), index=selected)
            except:
                return pd.Series(1 / len(selected), index=selected)

        raise ValueError("Unknown anchor method")

    def __call__(self, target):
        # Get selected assets and check minimum requirements
        selected = target.temp.get("selected", [])
        if len(selected) == 0:
            target.temp["weights"] = {}
            return True
        if len(selected) == 1:
            target.temp["weights"] = {selected[0]: 1.0}
            return True

        # Get required data from target
        t0 = target.now - self.lag
        prices = target.universe.loc[t0 - self.lookback:t0, selected]
        returns = prices.to_returns().dropna()

        # Get signal vector from target temp
        signal = target.temp.get("signal", pd.Series(1, index=selected))
        if len(signal) != len(selected):
            raise ValueError("Signal vector length mismatch with selected assets")

        # Covariance matrix calculation
        vcov = returns.cov()
        corr = returns.corr()
        n = len(selected)
        I = np.eye(n)

        # Shrinkage correlation matrix
        shrunk_cor = (1 - self.w) * corr + self.w * I  # Adjusted formula

        # Compute shrunk covariance matrix
        std = np.diag(np.sqrt(np.diag(vcov)))
        cov_tilde = std @ shrunk_cor @ std

        try:
            inv_shrunk_cov = np.linalg.inv(cov_tilde)
        except np.linalg.LinAlgError:
            raise ValueError("Singular matrix - cannot compute inverse covariance")

        # Compute EPO weights
        if self.method == "simple":
            epo_weights = (1 / self.lambda_) * inv_shrunk_cov @ signal.values
        elif self.method == "anchored":
            if self.anchor is None:
                raise ValueError("Anchor vector required for anchored method")

            a = self.anchor.values
            if self.endogenous:
                gamma = np.sqrt(a.T @ cov_tilde @ a) / np.sqrt(
                    signal.T @ inv_shrunk_cov @ cov_tilde @ inv_shrunk_cov @ signal
                )
                epo_weights = inv_shrunk_cov @ ((1 - self.w) * gamma * signal + self.w * std @ a)
            else:
                epo_weights = inv_shrunk_cov @ (
                        (1 - self.w) * (1 / self.lambda_) * signal + self.w * std @ a
                )

        # Normalization
        if self.normalize:
            epo_weights = np.clip(epo_weights, 0, None)  # Set negative weights to 0
            epo_weights /= epo_weights.sum()

        # Convert to dictionary format
        target.temp["weights"] = dict(zip(selected, epo_weights))

        return True

class SelectTopK(bt.AlgoStack):
    def __init__(self, signal, K, dropN=0, sort_descending=True, all_or_none=False, filter_selected=True):
        super(SelectTopK, self).__init__(bt.algos.SetStat(signal),
                                         bt.algos.SelectN(int(K) + int(dropN), sort_descending, all_or_none, filter_selected))
        self.dropN = dropN

    def __ceil__(self, target):
        super(SelectTopK, self).__ceil__()
        if self.dropN > 0:
            sel = target.temp["selected"]
            if self.dropN >= len(sel):
                target.temp['selected'] = []
            else:
                target.temp["selected"] = target.temp["selected"][self.dropN:]
            return True


from datafeed.dataloader import CSVDataloader
from datetime import datetime
from matplotlib import rcParams
from dataclasses import dataclass, field

rcParams['font.family'] = 'SimHei'


@dataclass
class MultiStrategies:
    name: str = '多策略组合'
    id_or_symbols: List[str] = field(default_factory=list)  # 策略组合的id
    start_date: str = '20200101'
    end_date: str = None
    # benchmark: str = '510300.SH'
    benchmark: str = '600000.SH'
    weight: str = 'WeighEqually'
    select: str = 'SelectAll'
    weight_fixed: Dict[str, int] = field(default_factory=dict)
    period: str = 'RunMonthly'


@dataclass
class Task:
    name: str = '策略'
    symbols: List[str] = field(default_factory=list)

    start_date: str = '20200101'   # 基准股 需从2010年1月1日开始
    end_date: str = None

    # benchmark: str = '510300.SH'
    benchmark: str = '600000.SH'
    select: str = 'SelectAll'

    select_buy: List[str] = field(default_factory=list)
    buy_at_least_count: int = 0
    select_sell: List[str] = field(default_factory=list)
    sell_at_least_count: int = 1

    order_by_signal: str = ''
    order_by_topK: int = 1
    order_by_dropN: int = 0
    order_by_DESC: bool = True  # 默认从大至小排序

    weight: str = 'WeighEqually'
    weight_fixed: Dict[str, int] = field(default_factory=dict)
    period: str = 'RunDaily'
    period_days: int = None


@dataclass
class StrategyConfig:
    name: str = '策略'
    desc: str = '策略描述'
    config_json: Dict[str, int] = field(default_factory=dict)
    author: str = ''


import importlib


class Engine:
    def __init__(self, path='quotes'):
        self.path = path

    def _parse_rules(self, task: Task, df):

        def _rules(df, rules, at_least):
            if not rules or len(rules) == 0:
                return None

            all = None
            for r in rules:
                if r == '':
                    continue

                df_r = CSVDataloader.get_col_df(df, r)
                if df_r is not None:
                    df_r = df_r.astype(int)
                else:
                    print(r)
                if all is None:
                    all = df_r
                else:
                    all += df_r
            return all >= at_least

        buy_at_least_count = task.buy_at_least_count
        if buy_at_least_count <= 0:
            buy_at_least_count = len(task.select_buy)

        all_buy = _rules(df, task.select_buy, at_least=buy_at_least_count)
        all_sell = _rules(df, task.select_sell, task.sell_at_least_count)  # 卖出 求或，满足一个即卖出
        return all_buy, all_sell

    def _get_algos(self, task: Task, df):

        bt_algos = importlib.import_module('bt.algos')

        if task.period == 'RunEveryNPeriods':
            algo_period = bt.algos.RunEveryNPeriods(n=task.period_days,run_on_last_date=True)
        else:
            algo_period = getattr(bt_algos, task.period)(run_on_last_date=True)

        algo_select_where = None
        # 信号规则
        signal_buy, signal_sell = self._parse_rules(task, df)
        if signal_buy is not None or signal_sell is not None:  # 至少一个不为None
            df_close = CSVDataloader.get_col_df(df, 'close')
            if signal_buy is None:
                select_signal = np.ones(df_close.shape)  # 注意这里是全1，没有select_buy就是全选
                select_signal = pd.DataFrame(select_signal, columns=df_close.columns, index=df_close.index)
            else:
                select_signal = np.where(signal_buy, 1, np.nan)  # 有select_buy的话，就是买入，否则选置Nan表示 hold状态不变
            if signal_sell is not None:
                select_signal = np.where(signal_sell, 0, select_signal)  # select_sell置为0，就是清仓或不选
            select_signal = pd.DataFrame(select_signal, index=df_close.index, columns=df_close.columns)
            select_signal.ffill(inplace=True)  # 这一句非常关键，ffill就是前向填充，保持持仓状态不变。即不符合buy，也不符合sell，保持不变。
            select_signal.fillna(0, inplace=True)
            algo_select_where = bt.algos.SelectWhere(signal=select_signal)

        # 排序因子
        algo_order_by = None
        if task.order_by_signal:
            signal_order_by = CSVDataloader.get_col_df(df, col=task.order_by_signal)
            algo_order_by = SelectTopK(signal=signal_order_by, K=task.order_by_topK, dropN=task.order_by_dropN,
                                       sort_descending=task.order_by_DESC)

        algos = []
        algos.append(algo_period)

        if algo_select_where:
            algos.append(algo_select_where)
        else:
            algos.append(bt.algos.SelectAll())

        if algo_order_by:
            algos.append(algo_order_by)

        if task.weight == 'WeighERC':
            algos.insert(0, bt.algos.RunAfterDays(days=256))
            algo_weight = getattr(bt_algos, task.weight)()
        elif task.weight == 'WeighSpecified':
            print(task.weight_fixed)
            algo_weight = bt.algos.WeighSpecified(**task.weight_fixed)
        elif task.weight == 'WeighEPO':
            algo_weight = WeighEPO(
            anchor_method='mean',
            w=0.2,
            lambda_=0.5,
            anchor_lookback=pd.DateOffset(months=10)
)

        else:
            if task.weight == 'WeighInVol':
                task.weight = 'WeighInvVol'
            algo_weight = getattr(bt_algos, task.weight)()

        algos.append(algo_weight)
        algos.append(bt.algos.Rebalance())

        return algos

    def run_tasks(self, tasks: list[Task]):
        bkts = []
        benchmarks = []
        for task in tasks:
            # 加载数据
            df = CSVDataloader.get_df(task.symbols, True, task.start_date, task.end_date)

            # 计算因子
            if len(task.symbols):
                fields = list(set(task.select_buy + task.select_sell + [task.order_by_signal]))
                names = fields
                if len(fields):
                    df = CSVDataloader.calc_expr(df, fields, names=names)

            s = bt.Strategy(task.name, self._get_algos(task, df))

            df_close = CSVDataloader.get_col_df(df, 'close')
            bkt = bt.Backtest(s, df_close, name=task.name)
            bkts.append(bkt)
            benchmarks.append(task.benchmark)

        for bench in list(set(benchmarks)):
            data = CSVDataloader.get([bench])
            s = bt.Strategy(bench, [bt.algos.RunOnce(),
                                    bt.algos.SelectAll(),
                                    bt.algos.WeighEqually(),
                                    bt.algos.Rebalance()])
            stra = bt.Backtest(s, data, name="基准:" + bench)
            bkts.append(stra)

        if bkts:
            res = bt.run(*bkts)
            # res.get_transactions()
            self.res = res
            return res
        else:
            raise Exception("没有可执行的任务")
            return None

    def _get_bkt(self, task):
        if type(task) is str:
            return task

        df = CSVDataloader.get_df(task.symbols, True, task.start_date, task.end_date, path=self.path)

        # 计算因子
        if len(task.symbols):
            print(task)
            fields = list(set(task.select_buy + task.select_sell + [task.order_by_signal]))
            names = fields
            if len(fields):
                df = CSVDataloader.calc_expr(df, fields, names=names)

        s = bt.Strategy(task.name, self._get_algos(task, df))

        df_close = CSVDataloader.get_col_df(df, 'close')
        bkt = bt.Backtest(s, df_close, name='策略')
        return bkt

    def run(self, task: Task):

        bkt = self._get_bkt(task)

        bkts = [bkt]
        for bench in [task.benchmark]:
            data = CSVDataloader.get([bench], path=self.path)
            s = bt.Strategy(bench, [bt.algos.RunOnce(),
                                    bt.algos.SelectAll(),
                                    bt.algos.WeighEqually(),
                                    bt.algos.Rebalance()])
            stra = bt.Backtest(s, data, name='benchmark',progress_bar=True)
            bkts.append(stra)

        res = bt.run(*bkts)
        # res.get_transactions()
        self.res = res
        return res

    def _get_task_by_id(self, id: str):
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

        return astock_rolling()

    def run_multi_tasks(self, strategy: MultiStrategies):
        tasks = []
        for t in strategy.id_or_symbols:
            if len(t) < 10:
                tasks.append(t)
            else:
                tasks.append(self._get_task_by_id(t))

        instruments = []
        for t in tasks:
            if type(t) is Task:
                instruments.extend(t.symbols)
            else:
                instruments.append(t)
        instruments = list(set(instruments))
        data = CSVDataloader.get_df(instruments, set_index=True, start_date=strategy.start_date)
        data.dropna(inplace=True)
        df_close = CSVDataloader.get_col_df(data)
        print(df_close)

        children = []
        for t in tasks:
            if type(t) is str:
                children.append(t)
            else:
                children.append(self._get_bkt(t).strategy)

        bt_algos = importlib.import_module('bt.algos')

        combined_strategy = bt.Strategy(
            strategy.name,
            algos=[
                getattr(bt_algos, strategy.period)(),
                getattr(bt_algos, strategy.select)(),
                # bt.algos.SelectAll(),
                # bt.algos.WeighInvVol(),
                getattr(bt_algos, strategy.weight)(),
                bt.algos.Rebalance()
            ],
            children=children
        )

        combined_test = bt.Backtest(
            combined_strategy,
            df_close,
            integer_positions=False,
            progress_bar=False
        )

        res = bt.run(combined_test)
        return res

    def get_equities(self):
        quotes = (self.res.prices.pct_change() + 1).cumprod().dropna()
        quotes['date'] = quotes.index
        # quotes['date'] = quotes['date'].apply(lambda x: x.strftime('%Y%m%d'))
        quotes.index = pd.to_datetime(quotes.index).map(lambda x: x.value)
        quotes = quotes[['策略', 'benchmark']]
        dict = quotes.to_dict(orient='series')

        results = {}
        for k, s in dict.items():
            result = list(zip(s.index, s.values))
            results[k] = result
        print(results)


import requests, json

if __name__ == '__main__':
    t = Task()
    t.name = '全球大类资产-等权重-月度再平衡'
    t.symbols = [
        '159934.SZ',  # 黄金ETF（黄金）
        # '511260.SH',  # 十年国债ETF（债券）
        '512890.SH',
        '512890.SH',  # 红利低波（股票）
        '159985.SZ',  # 豆粕（商品）
        '513100.SH'  # 纳指100
    ]
    t.period = 'RunMonthly'

    # config = StrategyConfig(name=t.name, desc='股票、债券、商品，黄金全球大类资产-等权重-月度再平衡，这是一个基准策略', config_json=asdict(t))
    # config.author = '678e02e71db30668ad7221e5'
    # put_task(config, task_id='678f5151ae544c859c97e06d')
    e = Engine()
    res = e.run(t)
    print(res.stats)
    print(res.get_security_weights().iloc[-1].to_dict())
    print(res.get_weights())
    # import matplotlib.pyplot as plt
    # res.plot()
    # plt.show()
