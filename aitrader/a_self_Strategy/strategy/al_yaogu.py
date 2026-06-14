import random
import akshare as ak
import pandas as pd
import numpy as np
from datetime import datetime
from ..untils.stocks_Info import Stock_Info
from common.logger import logger
import requests
import time
from common.readFile import ReadFile



confJson = ReadFile.read_json()


class YaoguQibaoAnalysis:
    """
    妖股起爆信号识别--综合信号：量价共振 + 技术形态 + 筹码分布
        1、量能条件：当日量能超过3倍5日均量
        2、价格突破条件：突破前高
        3、MACD条件：零上金叉且红柱持续放大
        4、筹码集中度条件：集中度90<20%, 低位单峰密集且快速上移
        5、大单净流入条件：大单净流入占比20%以上
    """


    def __init__(self, stock_code):
        self.stock_code = stock_code
        self.hist_data = None
        self.fund_flow = None
        self.cyq_data = None
        self.start_date = confJson.get('开始时间')
        self.end_date = datetime.now().strftime('%Y%m%d')
    def fetch_data(self):
        """
        获取基础数据：历史行情、资金流向、筹码分布
        """
        max_retries = 3
        retry_delay = 3  # seconds

        # 获取历史行情数据（后复权）
        for attempt in range(max_retries):
            try:
                print(f'获取历史行情数据:{self.stock_code},开始时间:{self.start_date},结束时间:{self.end_date}')
                self.hist_data = Stock_Info.get_stock_hist_data(
                    symbol=self.stock_code, start_date=self.start_date,
                    end_date=self.end_date, period="daily", adjust="hfq"
                )
                print(f'hist_data可用列:{self.hist_data.columns.tolist()}')
                break
            except (requests.exceptions.RequestException, pd.errors.ParserError) as e:
                if attempt < max_retries - 1:
                    print(f"获取历史行情数据失败，{retry_delay}秒后重试... (尝试 {attempt + 1}/{max_retries})")
                    time.sleep(retry_delay)
                else:
                    print("获取历史行情数据失败：超过最大重试次数")
                    self.hist_data = pd.DataFrame()

        # 获取资金流向数据（个股全量，含大单净流入-净占比）
        try:
            self.fund_flow = Stock_Info.get_fund_flowInfo(symbol=self.stock_code, type='all')
        except Exception as e:
            logger.warning(f"[{self.stock_code}] 获取资金流向失败: {e}")
            self.fund_flow = pd.DataFrame()

        # 获取筹码分布数据
        self.cyq_data = Stock_Info.get_cyq_data(self.stock_code)

        return {
            'hist_data': self.hist_data,
            'fund_flow': self.fund_flow,
            'cyq_data': self.cyq_data
        }

    def feature_engineering(self):
        """
        特征工程：生成成交量异动、均线系统、技术指标等特征
        """
        if self.hist_data is None or self.hist_data.empty:
            logger.warning(f"[{self.stock_code}] hist_data 为空，跳过特征工程")
            return pd.DataFrame()

        if '成交量' not in self.hist_data.columns:
            logger.warning(f"[{self.stock_code}] hist_data 缺少'成交量'列，当前列: {self.hist_data.columns.tolist()}")
            return pd.DataFrame()

        # 计算5日平均成交量
        self.hist_data['avg_volume_5'] = self.hist_data['成交量'].rolling(5).mean()

        # 计算5日、10日、20日均线
        self.hist_data['ma5'] = self.hist_data['收盘'].rolling(5).mean()
        self.hist_data['ma10'] = self.hist_data['收盘'].rolling(10).mean()
        self.hist_data['ma20'] = self.hist_data['收盘'].rolling(20).mean()

        # 计算MACD指标
        exp12 = self.hist_data['收盘'].ewm(span=12, adjust=False).mean()
        exp26 = self.hist_data['收盘'].ewm(span=26, adjust=False).mean()
        self.hist_data['macd'] = exp12 - exp26
        self.hist_data['signal'] = self.hist_data['macd'].ewm(span=9, adjust=False).mean()
        self.hist_data['histogram'] = self.hist_data['macd'] - self.hist_data['signal']

        # 生成MACD金叉信号
        self.hist_data['macd_golden_cross'] = (self.hist_data['macd'] > self.hist_data['signal']) & \
                                              (self.hist_data['macd'].shift(1) <= self.hist_data['signal'].shift(1))

        # 计算KDJ指标
        low_min = self.hist_data['最低'].rolling(9).min()
        high_max = self.hist_data['最高'].rolling(9).max()
        self.hist_data['fast_k'] = 100 * (self.hist_data['收盘'] - low_min) / (high_max - low_min)
        self.hist_data['slow_k'] = self.hist_data['fast_k'].rolling(3).mean()
        self.hist_data['slow_d'] = self.hist_data['slow_k'].rolling(3).mean()

        # 生成KDJ超买信号（J值>80）
        self.hist_data['kdj_overbought'] = (self.hist_data['slow_d'] > 80)

        return self.hist_data

    def yaogu_signal(self):
        """
        妖股起爆信号识别--综合信号：量价共振 + 技术形态 + 筹码分布
        """
        if len(self.hist_data) < 30:
            logger.info("历史数据不足30天，无法进行信号识别")
            return  False
        latest_data = self.hist_data.iloc[-1]

        # 量能条件：当日量能超过3倍5日均量
        volume_condition = latest_data['成交量'] > 3 * self.hist_data['avg_volume_5'].iloc[-1]

        # 价格突破条件：突破前高
        price_breakout = latest_data['收盘'] > self.hist_data['最高'].rolling(30).max().iloc[-2]

        # MACD条件：零上金叉且红柱持续放大
        macd_condition = (latest_data['macd'] > latest_data['signal']) and \
                         (latest_data['histogram'] > self.hist_data['histogram'].iloc[-2]) and \
                         (latest_data['macd'] > 0)

        # 筹码集中度条件：集中度90<20%, 低位单峰密集且快速上移
        if self.cyq_data is None or self.cyq_data.empty:
            cyq_condition = False
        else:
            avg_cost = pd.to_numeric(self.cyq_data.iloc[:, 1], errors='coerce')
            concentration_90 = pd.to_numeric(
                self.cyq_data.get('90集中度', self.cyq_data.iloc[:, -1]), errors='coerce'
            ) if hasattr(self.cyq_data, 'get') else pd.to_numeric(self.cyq_data.iloc[:, -1], errors='coerce')
            if '90集中度' in self.cyq_data.columns:
                concentration_90 = pd.to_numeric(self.cyq_data['90集中度'], errors='coerce')

            # ① 集中度90 < 20%（筹码高度集中）
            conc_90_ok = bool(concentration_90.iloc[-1] < 20)

            # ② 低位筹码：加权均价低于当前收盘价（主力成本低于市价，筹码锁定在低位）
            current_price = latest_data['收盘']
            low_position = bool(avg_cost.iloc[-1] < current_price)

            # ③ 快速上移：近5日加权均价单调递增（至少3日上涨）
            if len(avg_cost) >= 5:
                rising = int((avg_cost.iloc[-5:].diff().dropna() > 0).sum()) >= 3
            else:
                rising = False

            cyq_condition = conc_90_ok and low_position and rising

        # 大单净流入条件：大单净流入-净占比 >= 20%
        fund_flow_condition = False
        if self.fund_flow is not None and not self.fund_flow.empty:
            latest_fund = self.fund_flow.iloc[-1]
            for col in ('大单净流入-净占比', '主力净流入-净占比'):
                if col in self.fund_flow.columns:
                    val = pd.to_numeric(latest_fund[col], errors='coerce')
                    fund_flow_condition = bool(val >= 20)
                    break

        # 综合信号：量价共振 + 价格突破 + MACD技术形态 + 筹码分布 + 大单净流入
        signal_strength = sum([volume_condition, price_breakout, macd_condition,
                                cyq_condition, fund_flow_condition])

        return {
            'stock_code': self.stock_code,
            'date': datetime.now().strftime('%Y-%m-%d'),
            'volume_condition': volume_condition,
            'price_breakout': price_breakout,
            'macd_condition': macd_condition,
            'cyq_condition': cyq_condition,
            'fund_flow_condition': fund_flow_condition,
            'signal_strength': signal_strength,
            'total_conditions': 5,
            'final_signal': signal_strength >= 3  # 5个条件满足3个即触发
        }


def  yaogu_qibao_test(stock_list=''):
    """
    测试妖股起爆点分析框架
    :param stock_list: 股票代码列表
    :return: 妖股起爆信号列表
    """
    signals = []
    yaogu_stock_list = []
    if stock_list == '':
        stock_list = Stock_Info.my_stock_from_excel()
    stock_list_flow = Stock_Info.get_stocks_list_flowInfo(stock_list)
    logger.info(f"资金流入股票stock_list_flow：{stock_list_flow}")
    if stock_list_flow:
        stock_list = stock_list_flow  # 筛选主力资金流入>10%
    else:
        logger.info("筛选主力资金流入>10% 为空")
    # stock_list = Stock_Info.get_realtime_data(stock_list, increase=8)  # 筛选涨幅< 8%的妖股

    for stock in stock_list:
        logger.info(f"开始分析股票: {stock}")
        round(random.uniform(0, 1), 1)
        analyzer = YaoguQibaoAnalysis(stock)
        data = analyzer.fetch_data()

        if analyzer.hist_data is None or analyzer.hist_data.empty:
            logger.warning(f"[{stock}] 历史数据为空，跳过")
            continue

        features = analyzer.feature_engineering()     # 特征工程
        if features is None or (isinstance(features, pd.DataFrame) and features.empty):
            logger.warning(f"[{stock}] 特征工程失败，跳过")
            continue

        signal = analyzer.yaogu_signal()     # 生成信号
        if not signal:
            logger.warning(f"[{stock}] 信号生成失败，跳过")
            continue

        print(f"获取数据： {data}， 特征工程结果: {features}, 妖股信号: {signal}")

        total = signal.get('total_conditions', 5)
        strength = signal['signal_strength']
        detail = (f"量能={signal['volume_condition']} 突破={signal['price_breakout']} "
                  f"MACD={signal['macd_condition']} 筹码={signal['cyq_condition']} "
                  f"大单={signal.get('fund_flow_condition', False)}")
        if signal['final_signal']:
            print(f"{stock} pass-符合妖股起爆条件,信号强度: {strength}/{total} [{detail}]")
            yaogu_stock_list.append(stock)
            signals.append({
                'stock_code': stock,
                'signal': signal['final_signal'],
                'signal_strength': strength,
                'detail': detail
            })
        else:
            print(f"{stock} fail-不符合妖股起爆条件,信号强度: {strength}/{total} [{detail}]")

    # logger.info(f"al_yaogu.py 最终妖信号分析结果: {signals}")
    logger.info(f"al_yaogu.py 最终妖结果: {yaogu_stock_list}")
    return yaogu_stock_list



if __name__ == "__main__":

    yaogu_qibao_test()