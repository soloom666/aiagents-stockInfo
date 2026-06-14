import json
import random
import time
from datetime import datetime, timedelta
import akshare as ak
import talib
import pandas as pd
import plotly.graph_objects as go
from tenacity import retry

from common.readFile import ReadFile
from aitrader.a_self_Strategy.untils.stocks_Info import Stock_Info  # Fixed typo in folder name (untils -> utils)
from common.logger import logger
import baostock as bs
import backtrader as bt



confJson = ReadFile.read_json()
# Improved configuration handling with defaults
startdate = confJson.get('开始时间')  # Added default value
enddate = confJson.get('结束时间')
if not enddate or enddate == '':  # Added more robust empty check
    enddate = datetime.now().strftime('%Y%m%d')

def computeMACD(code, startdate, enddate):
    """
    macd 金叉、死叉、两次金叉
    """
    login_result = bs.login(user_id='anonymous', password='123456')
    if login_result.error_code != '0':
        logger.error(f"Baostock登录失败: {login_result.error_msg}")
        return None
    
    try:
        ###获取股票日K线数据###
        try:
            rs = bs.query_history_k_data_plus(code,
                                     "date,code,close,tradeStatus",
                                     start_date=startdate, end_date=enddate,
                                     frequency="d", adjustflag="3")
            #### 打印结果集 ####
            result_list = []
            while (rs.error_code == '0') & rs.next():
                # 获取一条记录，将记录合并在一起
                result_list.append(rs.get_row_data())
            
            df = pd.DataFrame(result_list, columns=rs.fields)
            # 剔除停盘数据
            df2 = df[df['tradeStatus'] == '1']
            
        except Exception as e:
            logger.error(f"获取{code}历史数据失败: {str(e)}")


        # 获取dif,dea,hist，它们的数据类似是tuple，且跟df2的date日期一一对应
        # 记住了dif,dea,hist前33个为Nan，所以推荐用于计算的数据量一般为你所求日期之间数据量的3倍
        # 这里计算的hist就是dif-dea,而很多证券商计算的MACD=hist*2=(dif-dea)*2
        dif, dea, hist = talib.MACD(df2['close'].astype(float).values, fastperiod=12, slowperiod=26, signalperiod=9)
        df3 = pd.DataFrame({'dif': dif[33:], 'dea': dea[33:], 'hist': hist[33:]},
                           index=df2['date'][33:], columns=['dif', 'dea', 'hist'])
        df3.plot(title='MACD')
        # plt.show()
        # 寻找MACD金叉和死叉
        datenumber = int(df3.shape[0])
        #  寻找MACD两次金叉 （1个月内短时间两次金叉 可能主力启动）
        gold_cross_dates = []
        for i in range(datenumber - 1):
            if ((df3.iloc[i, 0] <= df3.iloc[i, 1]) & (df3.iloc[i + 1, 0] >= df3.iloc[i + 1, 1])):
                print(code + "--MACD金叉的日期：" + df3.index[i + 1])
                gold_cross_dates.append(df3.index[i + 1])
            if ((df3.iloc[i, 0] >= df3.iloc[i, 1]) & (df3.iloc[i + 1, 0] <= df3.iloc[i + 1, 1])):
                print(code + "--MACD死叉的日期：" + df3.index[i + 1])

        # 判断是否有两次金叉:30天内有两次金叉
        if len(gold_cross_dates) >= 2 and abs((pd.to_datetime(gold_cross_dates[0]) - pd.to_datetime(gold_cross_dates[1])).days) <= 30:
            print("发现两次MACD金叉，日期分别为：", gold_cross_dates[0], "和", gold_cross_dates[1])
        else:
            print("未发现两次MACD金叉")

        bs.logout()
        return (dif, dea, hist)
    except Exception as e:
        logger.error(f"计算MACD时出现异常: {str(e)}")
        return None


def macd_boll(code, startdate, enddate):
    """
    捉妖神器：MACD+布林带适合妖股， 不太适用平台所有股
    """
    # 获取股票历史数据
    logger.info(f'获取股票历史信息code:{code},startdate:{startdate},enddate:{enddate}')
    try:
        time.sleep(random.randint(1, 3))  #  随机休眠3到6秒 , 反限制IP
        # time.sleep(random.uniform(3, 5))  # 获取历史数据--随机延迟3到5秒
        # df = ak.stock_zh_a_hist(symbol='600408', start_date='20250601', end_date='20251110', period="daily", adjust="")
        # 使用 baostock 替代 akshare
        df = Stock_Info.get_stock_hist_data(symbol=code, start_date=startdate, end_date=enddate, period="daily", adjust="")
        logger.info(f'获取股票历史数据]：{df}')
        if df.empty:
            logger.warning(f"{code} macd_boll从 baostock 获取的数据为空")
            return [], {}
        logger.info(f'macd_boll 获取股票历史数据可用列：{df.columns.tolist})')
        date_col = [col for col in df.columns if '日期' in col or 'date' in col]
        if date_col:
            df[date_col[0]] = pd.to_datetime(df[date_col[0]])
            df.set_index(date_col[0], inplace=True)
        else:
            logger.warning("未找到日期列，请检查 akshare 返回数据结构")
    except Exception as e:
        logger.error(f"获取股票历史数据失败: {str(e)}")


    # df['日期'] = pd.to_datetime(df['日期'])
    # df.set_index('日期', inplace=True)
    print(f'macd_boll ak的stock_zh_a_hist数据 df: \n {df}')
    # 指标计算  计算MACD
    df['DIF'], df['DEA'], df['MACD_hist'] = talib.MACD(
        df['收盘'],
        fastperiod=12,
        slowperiod=26,
        signalperiod=9
    )
    # 计算布林带
    df['upper'], df['middle'], df['lower'] = talib.BBANDS(
        df['收盘'],
        timeperiod=20,
        nbdevup=2,
        nbdevdn=2
    )

    # 触发信号条件
    # 检查必要的列是否存在
    required_columns = ['DIF', 'DEA', 'middle', '收盘', '成交量']
    missing_cols = [col for col in required_columns if col not in df.columns]
    if missing_cols:
        logger.warning(f"{code} 缺少必要列: {missing_cols}")
        return [], {}
        
    # MACD金叉条件（当日DIF>DEA且前一日DIF<DEA）
    df['MACD_金叉'] = (df['DIF'].shift(1) < df['DEA'].shift(1)) & (df['DIF'] > df['DEA'])
    # 价格突破布林带中轨（收盘价站上中轨且中轨趋势向上）
    df['中轨上扬'] = df['middle'].diff() > 0  # 中轨斜率>0
    df['突破中轨'] = df['收盘'] > df['middle']
    # 综合多头信号
    df['买入信号'] = df['MACD_金叉'] & df['突破中轨'] & df['中轨上扬']
    # df['买入信号'] = df['MACD_金叉'] & df['突破中轨']
    #策略优化与验证
    df['vol_ma20'] = talib.MA(df['成交量'], timeperiod=20)
    df['量能达标'] = df['成交量'] > df['vol_ma20'] * 1.2
    # logger.info(f"买入信号:{df['买入信号']}")

    #可视化示例: 绘制K线与布林带
    fig = go.Figure(data=[
        go.Candlestick(x=df.index, open=df['开盘'], high=df['最高'], low=df['最低'], close=df['收盘']),
        go.Scatter(x=df.index, y=df['middle'], line=dict(color='orange'), name='布林带中轨'),
        go.Scatter(x=df.index, y=df['upper'], line=dict(color='grey'), name='布林带上轨'),
        go.Scatter(x=df.index, y=df['lower'], line=dict(color='grey'), name='布林带下轨')
    ])

    # 标记买入信号点
    buy_signals = df[df['买入信号']]
    # logger.info(f"买入信号buy_signals:{buy_signals}")
    buy_signals_dates = buy_signals.index.strftime('%Y-%m-%d').tolist()
    logger.info(f"{code}:妖股买入日期:{buy_signals.index.strftime('%Y-%m-%d').tolist()}")
    buy_dict  = {
        "code": code,
        "buy_signals_dates": buy_signals_dates
    }
    fig.add_trace(go.Scatter(
        x=buy_signals.index,
        y=buy_signals['收盘'],
        mode='markers',
        marker=dict(color='green', size=10),
        name='买入信号'
    ))
    # fig.show()  # 显示图形
    return buy_signals_dates, buy_dict


def macd_boll_test(stock_list='',stockType='use', fast_mode=False):
    now_time = datetime.now().strftime('%Y-%m-%d')
    last_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')      # 获取最近2天的日期字符串
    print(now_time, last_date)
    buy_signals_list = []
    buy_signals_list_All = []
    if stock_list=='':
        stock_list = Stock_Info.get_stocks_info(stockType=stockType, stockList=stock_list)

    # for code in stock_list:
    for i in range(len(stock_list)):
        buy_signals_dates, buy_dict = macd_boll(code=stock_list[i], startdate=startdate, enddate=enddate)
        logger.info(f"第{i}次 code:{stock_list[i]}")
        if not fast_mode:
            time.sleep(random.randint(1, 2))  # 定时任务快速模式下跳过额外休眠
        if buy_signals_dates:
            buy_signals_list_All.append(buy_dict)
        if now_time in buy_signals_dates or last_date in buy_signals_dates:
            buy_signals_list.append(buy_dict)

    json_data_all = json.dumps(buy_signals_list_All, ensure_ascii=False, indent=4)
    json_data = json.dumps(buy_signals_list, ensure_ascii=False, indent=4)
    logger.info(f"所有汇总买入日期:{json_data_all}")
    logger.info(f"最近汇总买入日期:{json_data}")
    json_code_list = []
    json_obj = json.loads(json_data)  # 将JSON字符串解析为对象
    for i in range(len(json_obj)):
        json_code_list.append(json_obj[i]['code'])
    logger.info(f"macd_boll 妖股 json_code_list:{json_code_list}")
    return json_code_list


class MACDBollStrategy(bt.Strategy):
    params = (
        ('fast_period', 12),
        ('slow_period', 26),
        ('signal_period', 9),
        ('bb_period', 20),
        ('bb_dev', 2),
    )

    def __init__(self):
        self.dataclose = self.datas[0].close
        self.order = None
        self.buyprice = None
        self.buycomm = None

        # 添加MACD指标
        self.macd = bt.indicators.MACD(
            self.dataclose,
            period_me1=self.params.fast_period,
            period_me2=self.params.slow_period,
            period_signal=self.params.signal_period
        )

        # 添加布林带指标
        self.bbands = bt.indicators.BBands(
            self.dataclose,
            period=self.params.bb_period,
            devfactor=self.params.bb_dev
        )

    def next(self):
        if self.order:
            return

        if not self.position:
            if self.macd.macd[0] > self.macd.signal[0] and self.macd.macd[-1] < self.macd.signal[-1] and self.dataclose[0] > self.bbands.mid[0]:
                self.order = self.buy()

        else:
            if self.macd.macd[0] < self.macd.signal[0] and self.macd.macd[-1] > self.macd.signal[-1]:
                self.order = self.sell()

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(
                    'BUY EXECUTED, Price: %.2f, Cost: %.2f, Comm %.2f' %
                    (order.executed.price,
                     order.executed.value,
                     order.executed.comm))

                self.buyprice = order.executed.price
                self.buycomm = order.executed.comm
            else:  # Sell
                self.log('SELL EXECUTED, Price: %.2f, Cost: %.2f, Comm %.2f' %
                         (order.executed.price,
                          order.executed.value,
                          order.executed.comm))

            self.bar_executed = len(self)

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Order Canceled/Margin/Rejected')

        self.order = None

    def notify_trade(self, trade):
        if not trade.isclosed:
            return

        self.log('OPERATION PROFIT, GROSS %.2f, NET %.2f' %
                 (trade.pnl, trade.pnlcomm))

    def log(self, txt, dt=None):
        dt = dt or self.datas[0].datetime.date(0)
        print('%s, %s' % (dt.isoformat(), txt))


"""
TODO:  爪龙战法--预警通知

妖股启动前先亏2-3天洗掉散户，然后拉升
两次金叉 1个月内
死叉金叉 1个月内也可
龙头：一字涨停联板 排名靠前 板块绝对龙头


通信达app选股公式：VOL > REF(VOL, 1) * 1.5 AND CLOSE > REF(HHV(CLOSE, 30), 1) AND CROSS(MA(CLOSE,5), MA(CLOSE,10))

起爆点：
1、突破压力位-前一天>6% 前2天亏
2、成交量
3、死叉金叉 1个月内也可
4、人气股
5、当日成交量＞前5日均量3倍以上，且换手率＞8%
6、收盘价突破关键压力位（如60日/120日均线、前期高点或横盘平台上沿）



"""










if __name__ == '__main__':
    # macd_boll_test()
    # stock_list = Stock_Info.get_stocks_info('use')
    #目前趋势捉妖>macd——boll
    # stock_list = Stock_Info.my_stock_from_excel()
    # macd_boll_test(stock_list)

    # 测试：使用 baostock 替代 akshare
    # print(Stock_Info.get_stock_hist_data(symbol='002940', start_date='20250601', end_date='20251105', period="daily", adjust=""))
    # 筹码分布
    print(ak.stock_cyq_em(symbol='002262'))
