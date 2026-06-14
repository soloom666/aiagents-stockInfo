import math

import pandas as pd
from scipy.stats import skew

from datafeed import calc_by_symbol

import pandas as pd
import numpy as np


@calc_by_symbol
def shift(se: pd.Series, periods=5):
    return se.shift(periods=periods)


@calc_by_symbol
def ATR(high, low, close, timeperiod=14):
    # 计算前一日收盘价，第一个元素为NaN
    prev_close = close.shift(1)

    # 计算三个波动值
    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()

    # 计算真实波幅TR，当prev_close为NaN时（首日），仅取tr1
    tr = pd.Series(
        np.where(prev_close.isna(), tr1, np.maximum(np.maximum(tr1, tr2), tr3)),
        index=high.index
    )

    # 初始化ATR为TR的滚动平均值
    atr = tr.rolling(window=timeperiod, min_periods=timeperiod).mean()

    # 使用Wilder's平滑方法计算后续ATR
    for i in range(timeperiod, len(tr)):
        if pd.isna(atr.iloc[i]):
            prev_atr = atr.iloc[i - 1]
            current_tr = tr.iloc[i]
            atr.iloc[i] = (prev_atr * (timeperiod - 1) + current_tr) / timeperiod

    return atr


@calc_by_symbol
def ma_energy(close: pd.Series, window: int) -> pd.Series:
    # 计算移动平均线
    ma = close.rolling(window).mean()

    # 计算均线的差分
    diff = ma.diff()

    # 初始化方向序列，并根据差分确定方向
    direction = pd.Series(index=diff.index, dtype=float)
    direction[diff > 0] = 1  # 上涨
    direction[diff < 0] = -1  # 下跌
    direction[diff == 0] = 0  # 不变

    # 当差分无法计算时（如前一日均线为NaN），方向设为NaN
    direction[diff.isna()] = np.nan

    # 根据方向变化分组
    groups = (direction != direction.shift(1)).cumsum()

    # 创建掩码，排除方向为0和NaN的情况
    mask = (direction != 0) & (~direction.isna())

    # 计算各组的累积计数
    cumcount = mask.astype(int).groupby(groups).cumsum()

    # 计算能量值：方向 × 累积计数
    energy = direction * cumcount

    # 将均线无效位置的能量设为NaN
    energy[ma.isna()] = np.nan

    return energy


@calc_by_symbol
def trend_score(close, period=25):
    """
    向量化计算趋势评分：年化收益率 × R平方
    :param close: 收盘价序列（np.array或pd.Series）
    :param period: 计算窗口长度，默认25天
    :return: 趋势评分数组，长度与输入相同，前period-1位为NaN
    """
    if len(close) < period:
        return np.full_like(close, np.nan)

    y = np.log(close)
    windows = np.lib.stride_tricks.sliding_window_view(y, window_shape=period)
    x = np.arange(period)

    # 预计算固定值
    n = period
    sum_x = x.sum()
    sum_x2 = (x ** 2).sum()
    denominator = n * sum_x2 - sum_x ** 2

    # 滑动窗口统计量
    sum_y = windows.sum(axis=1)
    sum_xy = (windows * x).sum(axis=1)

    # 回归系数
    slope = (n * sum_xy - sum_x * sum_y) / denominator
    intercept = (sum_y - slope * sum_x) / n

    # 年化收益率
    annualized_returns = np.exp(slope * 250) - 1

    # R平方计算
    y_pred = slope[:, None] * x + intercept[:, None]
    residuals = windows - y_pred
    ss_res = np.sum(residuals ** 2, axis=1)

    sum_y2 = np.sum(windows ** 2, axis=1)
    ss_tot = sum_y2 - (sum_y ** 2) / n
    r_squared = 1 - (ss_res / ss_tot)
    r_squared = np.nan_to_num(r_squared, nan=0.0)  # 处理零方差情况

    # 综合评分
    score = annualized_returns * r_squared

    # 对齐原始序列长度
    full_score = np.full_like(y, np.nan)
    full_score = pd.Series(index=close.index)
    full_score[period - 1:] = score
    return full_score


import pandas as pd
import numpy as np



# 使用示例
# 假设 df 包含 High 和 Low 列
# df = calculate_rsrs(df)


@calc_by_symbol
def ts_corr(left: pd.Series, right: pd.Series, periods=20):
    res = left.rolling(window=periods).corr(right)
    # left.rolling(window=periods).apply(func=func,right)
    res.loc[
        np.isclose(left.rolling(periods, min_periods=1).std(), 0, atol=2e-05)
        | np.isclose(right.rolling(periods, min_periods=1).std(), 0, atol=2e-05)
        ] = np.nan
    return res


@calc_by_symbol
def ts_cov(left: pd.Series, right: pd.Series, periods=10):
    res = left.rolling(window=periods).cov(right)
    return res


# @calc_by_symbol
# def ts_beta(x, y, d):
#     x.ffill(inplace=True)
#     y.ffill(inplace=True)
#     z = talib.BETA(x, y, d)
#     return z


import numpy as np

from numpy.lib.stride_tricks import as_strided as strided


def rolling_window(a: np.array, window: int):
    '生成滚动窗口，以三维数组的形式展示'
    shape = a.shape[:-1] + (a.shape[-1] - window + 1, window)
    strides = a.strides + (a.strides[-1],)
    return strided(a, shape=shape, strides=strides)


def numpy_rolling_regress(x1, y1, window: int = 18, array: bool = False):
    """在滚动窗口内进行，每个矩阵对应进行回归"""
    x_series = np.array(x1)
    y_series = np.array(y1)
    # 创建一个一维数组
    dd = x_series
    x = rolling_window(dd, window)
    yT = rolling_window(y_series, window)
    y = np.array([i.reshape(window, 1) for i in yT])
    ones_vector = np.ones((1, x.shape[1]))
    XT = np.stack([np.vstack([ones_vector, row]) for row in x])  # 加入常数项
    X = np.array([matrix.T for matrix in XT])  # 以行数组表示
    reg_result = np.linalg.pinv(XT @ X) @ XT @ y  # 线性回归公示

    if array:
        return reg_result
    else:
        frame = pd.DataFrame()
        result_const = np.zeros(x_series.shape[0])
        const = reg_result.reshape(-1, 2)[:, 0]
        result_const[-const.shape[0]:] = const
        frame['const'] = result_const
        frame.index = x1.index
        for i in range(1, reg_result.shape[1]):
            result = np.zeros(x_series.shape[0])
            beta = reg_result.reshape(-1, 2)[:, i]
            result[-beta.shape[0]:] = beta
            frame[f'factor{i}'] = result
        return frame


@calc_by_symbol
def RSRS(high: pd.Series, low: pd.Series, N: int = 18):
    beta_series = numpy_rolling_regress(low, high, window=N, array=True)
    beta = beta_series.reshape(-1, 2)[:, 1]
    len_to_pad = len(low.index) - len(beta)
    pad = [np.nan for i in range(len_to_pad)]
    pad.extend(beta)
    beta = pd.Series(pad, index=low.index)
    return beta


@calc_by_symbol
def RSRS_zscore(high: pd.Series, low: pd.Series, N: int = 18, M: int = 600):
    beta_series = numpy_rolling_regress(low, high, window=N, array=True)
    beta = beta_series.reshape(-1, 2)[:, 1]

    beta_rollwindow = rolling_window(beta, M)
    beta_mean = np.mean(beta_rollwindow, axis=1)
    beta_std = np.std(beta_rollwindow, axis=1)
    zscore = (beta[M - 1:] - beta_mean) / beta_std
    len_to_pad = len(low.index) - len(zscore)
    # print(len_to_pad)
    pad = [np.nan for i in range(len_to_pad)]
    pad.extend(zscore)
    zscore = pd.Series(pad, index=low.index)
    return zscore


def r_rsrs(high: pd.Series, low: pd.Series, N: int = 18, M: int = 600):
    # 计算标准分
    zscore = RSRS_zscore(high, low, N, M)

    # 计算右偏标准分
    skewness = skew(zscore.dropna())  # 计算偏度
    right_skewed_zscore = zscore * (1 + skewness)  # 调整标准分以反映右偏

    return right_skewed_zscore

@calc_by_symbol
def kf2(series: pd.Series):
    from pykalman import KalmanFilter

    series = series.fillna(0.0)
    observation_covariance = 0.15
    initial_value_guess = 1
    transition_matrix = 1
    transition_covariance = 0.1

    kf = KalmanFilter(transition_matrices=[1],
                      observation_matrices=[1],
                      initial_state_mean=0,
                      initial_state_covariance=1,
                      observation_covariance=1,
                      transition_covariance=.01)
    pre, _ = kf.smooth(np.array(series))
    pre = pre.flatten()
    series = pd.Series(pre, index=series.index)
    return series


@calc_by_symbol
def kf(observations: pd.Series, damping_factor=0.9, initial_value=0):
    # 初始化
    observations.fillna(0.0, inplace=True)
    estimated_value = initial_value
    estimated_error = 1.0

    result = []
    for observation in observations:
        # 预测
        predicted_value = estimated_value
        predicted_error = estimated_error + (1 - damping_factor)

        # 更新
        kalman_gain = predicted_error / (predicted_error + 1)
        estimated_value = predicted_value + kalman_gain * (observation - predicted_value)
        estimated_error = (1 - kalman_gain) * predicted_error

        result.append(estimated_value)

    return pd.Series(result, index=observations.index)


@calc_by_symbol
def slope(close: pd.Series, d: int = 20):
    def _slope(close):
        y = np.log(close)
        x = np.arange(y.size)
        slope, intercept = np.polyfit(x, y, 1)
        annualized_returns = math.pow(math.exp(slope), 250) - 1
        r_squared = 1 - (sum((y - (slope * x + intercept)) ** 2) / ((len(y) - 1) * np.var(y, ddof=1)))
        score = annualized_returns * r_squared
        return score

    score = close.rolling(window=d).apply(lambda sub: _slope(sub))
    return score


@calc_by_symbol
def bbands_up(close, timeperiod=20, nbdevup=2, nbdevdn=2):
    # Initialize Bollinger Bands Indicator
    indicator_bb = BollingerBands(close, window=timeperiod, window_dev=nbdevup)

    upper_band = indicator_bb.bollinger_hband()
    # upper_band, middle_band, lower_band = talib.BBANDS(close, timeperiod=timeperiod, nbdevup=nbdevup, nbdevdn=nbdevdn)
    return upper_band


@calc_by_symbol
def bbands_down(close, timeperiod=20, nbdevup=2, nbdevdn=2):
    # Add Bollinger Band low indicator
    indicator_bb = BollingerBands(close, window=timeperiod, window_dev=nbdevup)
    lower_band = indicator_bb.bollinger_lband()
    # upper_band, middle_band, lower_band = talib.BBANDS(close, timeperiod=timeperiod, nbdevup=nbdevup, nbdevdn=nbdevdn)
    return lower_band
