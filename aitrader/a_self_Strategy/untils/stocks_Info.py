import random
import time
from datetime import datetime, timedelta
import akshare as ak
import pandas as pd
import requests
from common.logger import logger
import asyncio
import platform
from common.readFile import ReadFile
from aitrader.common.stockBasic import sh_or_sz
import os
import asyncio
import baostock as bs
try:
    import aiohttp
except ModuleNotFoundError:
    aiohttp = None

# 初始化 akshare 代理配置（防止 IP 被封）
from aitrader.common.proxy_config import ProxyConfig
ProxyConfig.init_akshare_proxy()

FAST_MODE = False


def _maybe_sleep(min_seconds=0.0, max_seconds=0.0):
    if FAST_MODE:
        return
    if max_seconds <= 0:
        return
    time.sleep(random.uniform(min_seconds, max_seconds))


# 修复 Windows 下 aiodns 报错问题
if platform.system() == "Windows":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

class Stock_Info:
    @staticmethod
    def set_fast_mode(enabled: bool):
        global FAST_MODE
        FAST_MODE = bool(enabled)

    @staticmethod
    def get_stock_hist_data(symbol, start_date, end_date, period="daily", adjust=""):
        """
        获取股票历史数据：优先使用 akshare，失败或无数据时降级到 baostock。

        参数:
            symbol: 股票代码，例如 "000001"
            start_date: 开始日期，格式 "YYYYMMDD"
            end_date: 结束日期，格式 "YYYYMMDD"
            period: 周期，"daily" / "weekly" / "monthly"
            adjust: 复权类型，"" 不复权, "qfq" 前复权, "hfq" 后复权

        返回:
            DataFrame，列名统一为中文（日期/开盘/最高/最低/收盘/成交量/成交额/换手率）
        """
        # ── 1. 优先尝试 akshare ────────────────────────────
        try:
            df = ak.stock_zh_a_hist(
                symbol=symbol,
                period=period,
                start_date=start_date,
                end_date=end_date,
                adjust=adjust
            )
            if df is not None and not df.empty:
                # 确保关键列存在
                required = {'日期', '开盘', '最高', '最低', '收盘', '成交量', '成交额', '换手率'}
                if required.issubset(set(df.columns)):
                    if '股票代码' not in df.columns:
                        df.insert(1, '股票代码', symbol)
                    logger.info(f"[akshare] 成功获取 {symbol} 历史数据，共 {len(df)} 条")
                    return df
                else:
                    missing = required - set(df.columns)
                    logger.warning(f"[akshare] {symbol} 返回数据缺少字段 {missing}，降级到 baostock")
            else:
                logger.warning(f"[akshare] {symbol} 返回数据为空，降级到 baostock")
        except Exception as e:
            logger.warning(f"[akshare] 获取 {symbol} 历史数据失败: {e}，降级到 baostock")

        # ── 2. 降级到 baostock ────────────────────────────
        login_result = bs.login()
        if login_result.error_code != '0':
            logger.error(f"[baostock] 登录失败: {login_result.error_msg}")
            return pd.DataFrame()

        try:
            # 转换股票代码格式
            if symbol.startswith('6'):
                bs_symbol = f'sh.{symbol}'
            elif symbol.startswith(('0', '3')):
                bs_symbol = f'sz.{symbol}'
            else:
                bs_symbol = f'sz.{symbol}'

            # 日期格式：YYYYMMDD -> YYYY-MM-DD
            start_date_formatted = f"{start_date[:4]}-{start_date[4:6]}-{start_date[6:]}"
            end_date_formatted = f"{end_date[:4]}-{end_date[4:6]}-{end_date[6:]}"

            frequency_map = {"daily": "d", "weekly": "w", "monthly": "m"}
            frequency = frequency_map.get(period, "d")

            # 复权类型：3-不复权 2-前复权 1-后复权
            adjust_map = {"": "3", "qfq": "2", "hfq": "1"}
            adjustflag = adjust_map.get(adjust, "3")

            rs = bs.query_history_k_data_plus(
                bs_symbol,
                "date,code,open,high,low,close,volume,amount,turn",
                start_date=start_date_formatted,
                end_date=end_date_formatted,
                frequency=frequency,
                adjustflag=adjustflag
            )

            result_list = []
            while (rs.error_code == '0') & rs.next():
                result_list.append(rs.get_row_data())

            if not result_list:
                logger.warning(f"[baostock] 未获取到 {symbol} 历史数据")
                bs.logout()
                return pd.DataFrame()

            df = pd.DataFrame(result_list, columns=rs.fields)
            df.rename(columns={
                'date': '日期', 'code': '股票代码',
                'open': '开盘', 'high': '最高', 'low': '最低', 'close': '收盘',
                'volume': '成交量', 'amount': '成交额', 'turn': '换手率'
            }, inplace=True)

            numeric_cols = ['开盘', '最高', '最低', '收盘', '成交量', '成交额', '换手率']
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')

            if '股票代码' in df.columns:
                df['股票代码'] = df['股票代码'].str.replace('sh.', '', regex=False).str.replace('sz.', '', regex=False)

            logger.info(f"[baostock] 成功获取 {symbol} 历史数据，共 {len(df)} 条")
            bs.logout()
            return df

        except Exception as e:
            logger.error(f"[baostock] 获取 {symbol} 历史数据失败: {e}")
            bs.logout()
            return pd.DataFrame()

    def my_stock_from_excel(fromfilePath='/aitrader/data/input/myStock/我的自选.xlsx'):
        try:
            # 从Excel读取股票代码
            df = ReadFile.read_fileNosheet(fromfilePath, 'xlsx')
            stockLists = []
            stockNameLists = []
            for index, row in df.iterrows():
                # stock = row['代码']
                # stockName = row['名称']
                stock = row['股票代码']
                if ".SH" in stock.upper() or '.SZ' in stock.upper():
                    stock = stock[:-3]
                else:
                    print(f'股票代码无后缀：{stock}')
                    # continue
                stockName = row['股票简称']
                stockLists.append(stock)
                stockNameLists.append(stockName)
            print(f'股code列表 stockLists：{stockLists}')
            print(f'股名称列表 stockNameLists：{stockNameLists}')
            return stockLists
        except Exception as e:
            logger.error(f'读取Excel代码拼接异常：{e}')



    def get_stocks_info(stockType, riseRate=1, stockList=''):
        """
        获取A股主板股票: stockType = 'all' 全部股票，'useful' 可操作的股票，'pe' 市盈率小于50 市净率小于3
        """
        stock_spot = ak.stock_zh_a_spot_em()
        required_columns = ['代码', '名称', '市盈率-动态', '市净率', '最新价', '涨跌幅', '成交量']
        missing_columns = [col for col in required_columns if col not in stock_spot.columns]
        if missing_columns:
            raise ValueError(f"缺失必要字段: {missing_columns}")
        filtered_stocks = stock_spot[required_columns]

        if stockType == 'all':
            EXCLUDE_KEYWORDS = '退市'
            quality_stock_condition = (
                    (~stock_spot["名称"].str.contains(EXCLUDE_KEYWORDS, case=False))
            )
        elif  stockType == 'use':
            # 排除ST、*ST、退市股、创业板（30）、科创板（688）、北交所（8）
            EXCLUDE_KEYWORDS = 'ST|退市'
            EXCLUDE_CODE = ('30', '688', '8')
            quality_stock_condition = (
                    (~stock_spot["名称"].str.contains(EXCLUDE_KEYWORDS, case=False)) &
                    (~stock_spot['代码'].str.startswith(EXCLUDE_CODE))
            )
        elif  stockType == 'rise':
            # 排除ST、*ST、退市股、创业板（30）、科创板（688）、北交所（8），涨幅5分钟1%
            EXCLUDE_KEYWORDS = 'ST|退市'
            EXCLUDE_CODE = ('30', '688', '8')
            quality_stock_condition = (
                    (~stock_spot["名称"].str.contains(EXCLUDE_KEYWORDS, case=False)) &
                    (stock_spot['5分钟涨跌'] > 0.01 * riseRate) &
                    (~stock_spot['代码'].str.startswith(EXCLUDE_CODE))
            )
        elif  stockType == 'pe':
            #市盈率小于50 市净率小于3
            quality_stock_condition = (
                    (stock_spot['市盈率-动态'] > 0) &
                    (stock_spot['市盈率-动态'] < 50) &
                    (stock_spot['市净率'] < 3) &
                    (~stock_spot["名称"].str.contains('ST|退市')) &
                    (~stock_spot['代码'].str.startswith(('30', '688', '8')))  # 排除创业跟科创板 北交所‘8’开头
            )
        elif  stockType == 'myStock':
            # 我的自选股
            if stockList=='':
                print('get_stocks_info从Excel中获取自选股列表')
                stockList = Stock_Info.my_stock_from_excel()
            quality_stock_condition = (
                    (stock_spot['涨跌幅'] < 0.066) &
                    # (stock_spot['5分钟涨跌'] > 0.01 * riseRate) &
                    (stock_spot['代码'].isin(stockList))
            )
        else:
            logger.info("实时获取股票信息 type有误！")
        filtered_stocks = stock_spot[quality_stock_condition][required_columns]
        stocksList = filtered_stocks.to_dict(orient="records")
        logger.info(f"股票数量：{len(stocksList)}")
        # logger.info(f"股票信息：{stocksList}")
        stock_codes_list = [item['代码'] for item in stocksList]
        # print(stock_codes)
        return stock_codes_list





    def get_stocks_All_info(stockType, stockList=[], riseRate=''):
        """
            所有列信息，市值<150亿，量比>1 ,'涨跌幅'] < 0.06 ,'5分钟涨跌'] < 0.01 * riseRate
        """
        time.sleep(random.uniform(0, 1))
        stock_spot = ak.stock_zh_a_spot_em()

        if stockType == 'all':
            EXCLUDE_KEYWORDS = '退市'
            quality_stock_condition = (
                    (~stock_spot["名称"].str.contains(EXCLUDE_KEYWORDS, case=False))
            )
        elif  stockType == 'use':
            # 排除ST、*ST、退市股、创业板（30）、科创板（688）、北交所（8）
            EXCLUDE_KEYWORDS = 'ST|退市'
            EXCLUDE_CODE = ('30', '688', '8')
            quality_stock_condition = (
                    (~stock_spot["名称"].str.contains(EXCLUDE_KEYWORDS, case=False)) &
                    (~stock_spot['代码'].str.startswith(EXCLUDE_CODE))
            )
        elif  stockType == 'rise':
            # 排除ST、*ST、退市股、创业板（30）、科创板（688）、北交所（8），涨幅5分钟1%
            EXCLUDE_KEYWORDS = 'ST|退市'
            EXCLUDE_CODE = ('30', '688', '8')
            quality_stock_condition = (
                    (~stock_spot["名称"].str.contains(EXCLUDE_KEYWORDS, case=False)) &
                    (stock_spot['涨跌幅'] < 0.066 ) &
                    (stock_spot['5分钟涨跌'] > 0.01 * riseRate) &
                    (stock_spot['流通市值'] < 150 * 10000000) &
                    (stock_spot['量比'] < 1 ) &
                    (~stock_spot['代码'].str.startswith(EXCLUDE_CODE))
            )
        elif  stockType == 'pe':
            #市盈率小于50 市净率小于3
            quality_stock_condition = (
                    (stock_spot['市盈率-动态'] > 0) &
                    (stock_spot['市盈率-动态'] < 50) &
                    (stock_spot['市净率'] < 3) &
                    (~stock_spot["名称"].str.contains('ST|退市')) &
                    (~stock_spot['代码'].str.startswith(('30', '688', '8')))  # 排除创业跟科创板 北交所‘8’开头
            )
        elif  stockType == 'myStock':
            # 我的自选股
            print("我的自选股：")
            if stockList is None or stockList == []:
                logger.info("从excel中获取自选股")
                stockList = Stock_Info.my_stock_from_excel()
            if riseRate == '':
                quality_stock_condition = (
                    (stock_spot['涨跌幅'] < 0.066) &
                    (stock_spot['代码'].isin(stockList))
                )
            else:
                quality_stock_condition = (
                    (stock_spot['涨跌幅'] < 0.066) &
                    (stock_spot['5分钟涨跌'] > 0.01 * riseRate) &
                    (stock_spot['代码'].isin(stockList))
                )
        else:
            logger.info("实时获取股票信息 type有误！")
        # filtered_stocks = stock_spot[quality_stock_condition][required_columns]
        filtered_stocks = stock_spot[quality_stock_condition]
        stocksList = filtered_stocks.to_dict(orient="records")
        print("实时行情stocksList：", stocksList)
        logger.info(f"股票数量：{len(stocksList)}")
        return filtered_stocks



    # 获取实时行情数据
    def get_realtime_data(stock_list, increase=0):
        max_retries = 3
        for attempt in range(max_retries):
            try:
                stock_spot = ak.stock_zh_a_spot_em()
                # 确保 stock_list 是列表格式，并兼容单个股票代码字符串的情况
                if isinstance(stock_list, str):
                    stock_code_list = [stock_list]
                else:
                    stock_code_list = stock_list
                if increase ==0:
                    quality_stock_condition = ((stock_spot['代码'].isin(stock_code_list)))
                    filtered_stocksInfo = stock_spot[quality_stock_condition]
                    print("实时行情列表：", filtered_stocksInfo.columns.tolist)
                    print("实时行情数据：", filtered_stocksInfo)
                    return filtered_stocksInfo
                else:
                    quality_stock_condition = ((stock_spot['涨跌幅'] < increase) &
                                               (stock_spot['代码'].isin(stock_code_list)))
                    filtered_stocksInfo = stock_spot[quality_stock_condition]
                    stock_codes_list = filtered_stocksInfo['代码'].tolist()  # 提取股票代码列表
                    filtered_stocksInfo.to_dict(orient="records")
                    print("实时行情筛选涨幅<8% 的stock_codes_list：", stock_codes_list)
                    return stock_codes_list
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # 指数退避
                    continue
                raise RuntimeError(f"API调用失败: {str(e)}") from e


    # 获取财务数据（ROE/PB/PE）
    def get_financial_data(stock_code):
        # return ak.stock_financial_analysis_indicator(symbol=stock_code)[['净资产收益率','市净率','市盈率']]
        _maybe_sleep(1, 3)
        financial_data = ak.stock_financial_abstract_ths(symbol=stock_code, indicator='按年度').tail(1)
        print("财务数据可用字段：", financial_data.columns.tolist())
        print("最近一年财务数据：", financial_data)
        # 倒序取最近5个季度数据
        latest_5_quarters = financial_data.tail(5)
        # 提取指定字段
        if '净资产收益率' in latest_5_quarters.columns:
            roe_data = latest_5_quarters['净资产收益率']
            print("最近5个季度 ROE：", roe_data.tolist())
        else:
            logger.error("字段 '净资产收益率' 不存在于财务数据中")
        return financial_data

    # 获取资金流向数据
    def get_capital_flow(stock_code):
        stockType = sh_or_sz(stock_code)

        try:
            _maybe_sleep(1, 3)
            data = ak.stock_individual_fund_flow(stock=stock_code, market=stockType).tail(1)
            if data.empty:
                logger.warning(f"{stock_code} 资金流向数据为空")
                return pd.DataFrame(columns=['主力净流入-净额', '超大单净流入-净额', '大单净流入-净额', '中单净流入-净额', '小单净流入-净额'])

            print("当天资金流向：", data[['主力净流入-净额', '超大单净流入-净额', '大单净流入-净额', '中单净流入-净额', '小单净流入-净额']])
            return data[['主力净流入-净额', '超大单净流入-净额', '大单净流入-净额', '中单净流入-净额', '小单净流入-净额']]

        except Exception as e:
            logger.error(f"获取资金流向失败: {e}")
            return pd.DataFrame()




    # 2. 获取半年内历史最高价
    def get_historical_high(symbol,days=180):
        end_date = datetime.now().strftime("%Y%m%d")
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y%m%d")
        _maybe_sleep(1, 3)
        # 使用 baostock 替代 akshare
        hist_data = Stock_Info.get_stock_hist_data(
            symbol=symbol, period="daily",
            start_date=start_date, end_date=end_date, adjust=""
        )
        print("历史数据：",hist_data)
        if not hist_data.empty and "最高" in hist_data.columns:
            print("历史数据最贵价：",hist_data["最高"].max())
            return hist_data["最高"].max()
        return None


    def get_stock_history(symbol, start_date, end_date):
        # if start_date is None or end_date is None:
        #     start_date = (datetime.now() - timedelta(days=180)).strftime("%Y%m%d")
        #     end_date = datetime.now().strftime("%Y%m%d")
        _maybe_sleep(1, 3)
        # 使用 baostock 替代 akshare
        hist_data = Stock_Info.get_stock_hist_data(symbol=symbol, period="daily",
            start_date=start_date, end_date=end_date, adjust="")
        print("历史数据可用列：",hist_data.columns.tolist())
        print("历史数据：",hist_data)
        return hist_data



    # 3. 获取主力资金净流入数据
    def get_fund_flow(symbol):
        try:
            _maybe_sleep(1, 3)
            stockType = sh_or_sz(symbol)
            fund_flow = ak.stock_individual_fund_flow(stock=symbol, market=stockType).tail(1)
            # latest_fund = fund_flow.iloc[0]  # 取最新一日数据
            fund_flow_money = fund_flow['主力净流入-净额'].values[0]
            print("当天资金流向：",fund_flow[['主力净流入-净额', '超大单净流入-净额', '大单净流入-净额', '中单净流入-净额', '小单净流入-净额']].values[0])
            # print("主力净流入：",fund_flow_money)
            return fund_flow_money
        except Exception as e:
            logger.error(f"获取资金流向失败: {e}")
        return pd.DataFrame()


    # 4. 内外盘
    def domestic_foreign_volumn(symbol):
        _maybe_sleep(1, 3)
        stock_bid_ask_em_df = ak.stock_bid_ask_em(symbol=symbol)
        domestic = float(stock_bid_ask_em_df[stock_bid_ask_em_df["item"] == "内盘"]["value"].values[0])
        foreign = float(stock_bid_ask_em_df[stock_bid_ask_em_df["item"] == "外盘"]["value"].values[0])
        # print(f'内盘信息：stock_bid_ask_em_df：{domestic}, 外盘信息：{foreign}')
        return domestic, foreign



    @staticmethod
    def _get_fund_flow_rank_baostock(stock_list: list) -> pd.DataFrame:
        """
        baostock 降级实现：用当日 K 线估算资金流向排名数据。
        - 今日主力净流入-净额  ≈ 成交额 × 涨跌幅 / 100
        - 今日主力净流入-净占比 ≈ 涨跌幅（pctChg）
        返回与 akshare stock_individual_fund_flow_rank 兼容的 DataFrame。
        """
        today = datetime.now().strftime("%Y-%m-%d")
        login_result = bs.login()
        if login_result.error_code != '0':
            logger.error(f"[baostock] 登录失败: {login_result.error_msg}")
            return pd.DataFrame()

        records = []
        try:
            for symbol in stock_list:
                bs_symbol = f'sh.{symbol}' if symbol.startswith('6') else f'sz.{symbol}'
                rs = bs.query_history_k_data_plus(
                    bs_symbol,
                    "date,code,close,volume,amount,pctChg",
                    start_date=today,
                    end_date=today,
                    frequency="d",
                    adjustflag="3"
                )
                while rs.error_code == '0' and rs.next():
                    row = rs.get_row_data()
                    try:
                        close  = float(row[2]) if row[2] else 0.0
                        amount = float(row[4]) if row[4] else 0.0
                        pct    = float(row[5]) if row[5] else 0.0
                        net_amount = amount * pct / 100
                        records.append({
                            '代码':               symbol,
                            '名称':               symbol,
                            '最新价':             close,
                            '今日涨跌幅':          pct,
                            '今日主力净流入-净额':  net_amount,
                            '今日主力净流入-净占比': pct,
                            '今日超大单净流入-净额':  0.0,
                            '今日超大单净流入-净占比': 0.0,
                            '今日大单净流入-净额':    0.0,
                            '今日大单净流入-净占比':  0.0,
                            '今日中单净流入-净额':    0.0,
                            '今日中单净流入-净占比':  0.0,
                            '今日小单净流入-净额':    0.0,
                            '今日小单净流入-净占比':  0.0,
                        })
                    except (ValueError, IndexError):
                        continue
        except Exception as e:
            logger.error(f"[baostock] 资金流向估算失败: {e}")
        finally:
            bs.logout()

        df = pd.DataFrame(records)
        logger.info(f"[baostock] 资金流向估算完成，共 {len(df)} 条（涨跌幅作为净占比代理）")
        return df

    @staticmethod
    def _get_fund_flow_rank(stock_list: list) -> pd.DataFrame:
        """
        获取今日资金流向排名：akshare 优先，失败降级 baostock。
        返回已按 stock_list 过滤的 DataFrame。
        """
        # 1. 优先 akshare
        try:
            df = ak.stock_individual_fund_flow_rank(indicator="今日")
            if df is not None and not df.empty:
                df['今日主力净流入-净占比'] = pd.to_numeric(df['今日主力净流入-净占比'], errors='coerce')
                result = df[df['代码'].isin(stock_list)]
                logger.info(f"[akshare] 资金流向排名获取成功，筛选出 {len(result)} 条")
                return result
            logger.warning("[akshare] stock_individual_fund_flow_rank 返回空，降级 baostock")
        except Exception as e:
            logger.warning(f"[akshare] stock_individual_fund_flow_rank 失败: {e}，降级 baostock")

        # 2. 降级 baostock
        df = Stock_Info._get_fund_flow_rank_baostock(stock_list)
        if not df.empty:
            df['今日主力净流入-净占比'] = pd.to_numeric(df['今日主力净流入-净占比'], errors='coerce')
        return df

    # 获取资金流入数据
    def get_fund_flowInfo(symbol='', stock_list=[], type='else'):
        try:
            stockType = sh_or_sz(symbol)
            if type == 'all':
                _maybe_sleep(1, 3)
                fund_flow = ak.stock_individual_fund_flow(stock=symbol, market=stockType)
            else:
                fund_flow = Stock_Info._get_fund_flow_rank(stock_list)

            print("当天资金流向：", fund_flow[['名称', '今日主力净流入-净额', '今日主力净流入-净占比']])
            return fund_flow
        except Exception as e:
            logger.error(f"获取资金流向失败: {e}")
        return pd.DataFrame()

    def get_stocks_list_flowInfo(stock_list):
        # 获取stocklist实时资金流向数据-筛选出今日主力净流入-净占比> 10的数据
        _maybe_sleep(1, 3)
        fund_flow = Stock_Info._get_fund_flow_rank(stock_list)

        if fund_flow.empty:
            logger.info("资金流向数据为空")
            return []

        # 筛选今日主力净流入-净占比 > 10 的股票
        fund_flow = fund_flow[fund_flow['今日主力净流入-净占比'] > 10]
        print("今日资金流向fund_flow：", fund_flow[['代码', '今日主力净流入-净额', '今日主力净流入-净占比']])

        if not fund_flow.empty:
            fund_flow_stockList = fund_flow['代码'].tolist()
            print(f'资金流向股票代码list：{fund_flow_stockList}')
            return fund_flow_stockList
        else:
            logger.info("今日主力净流入-净占比 > 10 为空！！！")
            return []
    @staticmethod
    def _cyq_from_baostock(symbol: str) -> pd.DataFrame:
        """
        baostock 降级实现：基于近 250 日 K 线用量价加权模型估算筹码分布。
        返回与 ak.stock_cyq_em 兼容的 DataFrame（仅最新一条记录）。

        估算逻辑：
          - 平均成本    = Σ(收盘价 × 成交量) / Σ(成交量)   [VWAP]
          - 获利比例    = 成本低于当日收盘价的成交量 / 总成交量
          - 70%/90% 集中度区间：按成交量累积分位数确定上下轨
        """
        end_date   = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")

        login_result = bs.login()
        if login_result.error_code != '0':
            logger.error(f"[baostock] 登录失败: {login_result.error_msg}")
            return pd.DataFrame()

        try:
            bs_symbol = f'sh.{symbol}' if symbol.startswith('6') else f'sz.{symbol}'
            rs = bs.query_history_k_data_plus(
                bs_symbol,
                "date,close,volume",
                start_date=start_date,
                end_date=end_date,
                frequency="d",
                adjustflag="3"
            )
            rows = []
            while rs.error_code == '0' and rs.next():
                rows.append(rs.get_row_data())
        except Exception as e:
            logger.error(f"[baostock] 筹码K线查询失败: {e}")
            bs.logout()
            return pd.DataFrame()
        finally:
            bs.logout()

        if not rows:
            return pd.DataFrame()

        kdf = pd.DataFrame(rows, columns=['date', 'close', 'volume'])
        kdf['close']  = pd.to_numeric(kdf['close'],  errors='coerce')
        kdf['volume'] = pd.to_numeric(kdf['volume'], errors='coerce')
        kdf.dropna(inplace=True)
        if kdf.empty:
            return pd.DataFrame()

        total_vol = kdf['volume'].sum()
        current   = kdf['close'].iloc[-1]
        today_str = kdf['date'].iloc[-1]

        # 平均成本（VWAP）
        avg_cost = (kdf['close'] * kdf['volume']).sum() / total_vol

        # 获利比例：成本价 < 当前价 的成交量占比
        profit_ratio = kdf.loc[kdf['close'] < current, 'volume'].sum() / total_vol * 100

        # 70%/90% 集中度区间（按成交量累积分位数）
        kdf_sorted = kdf.sort_values('close')
        kdf_sorted['cum_vol'] = kdf_sorted['volume'].cumsum() / total_vol

        def _price_at(q):
            row = kdf_sorted[kdf_sorted['cum_vol'] >= q].head(1)
            return float(row['close'].values[0]) if not row.empty else current

        p05, p95 = _price_at(0.05), _price_at(0.95)
        p15, p85 = _price_at(0.15), _price_at(0.85)

        result = pd.DataFrame([{
            '日期':     today_str,
            '获利比例':  round(profit_ratio, 2),
            '平均成本':  round(avg_cost, 2),
            '90集中度': round(p95 - p05, 2),
            '90上线':   round(p95, 2),
            '90下线':   round(p05, 2),
            '70集中度': round(p85 - p15, 2),
            '70上线':   round(p85, 2),
            '70下线':   round(p15, 2),
        }])
        logger.info(f"[baostock] 筹码估算完成: {symbol}  获利比例={profit_ratio:.1f}%  均成本={avg_cost:.2f}")
        return result

    def get_cyq_data(symbol):
        """获取筹码分布数据：akshare 优先，失败降级 baostock 估算。"""
        # ──1. 优先 baostock ───────────────────────────────
        cyq_data = Stock_Info._cyq_from_baostock(symbol)
        print(f'[baostock] 筹码估算数据:\n{cyq_data}')

        max_retries = 1
        retry_delay = 1
        # ──  2. 降级 akshare ────────────────────────────────
        cyq_data = pd.DataFrame()
        for attempt in range(max_retries):
            try:
                _maybe_sleep(3, 5)
                cyq_data = ak.stock_cyq_em(symbol=symbol)
                if isinstance(cyq_data, list):
                    cyq_data = pd.DataFrame(cyq_data)
                if not cyq_data.empty:
                    print(f'[akshare] cyq_data 可用列: {cyq_data.columns.tolist()}')
                    print(f'[akshare] 筹码分布数据:\n{cyq_data}')
                    return cyq_data
                logger.warning(f"[akshare] stock_cyq_em 返回空，降级 baostock")
                break
            except (requests.exceptions.RequestException, pd.errors.ParserError) as e:
                if attempt < max_retries - 1:
                    print(f"获取筹码分布数据失败，{retry_delay}秒后重试... (尝试 {attempt + 1}/{max_retries})")
                    time.sleep(retry_delay)
                else:
                    logger.warning(f"[akshare] stock_cyq_em 超过最大重试次数: {e}，降级 baostock")
            except Exception as e:
                logger.warning(f"[akshare] stock_cyq_em 异常: {e}，降级 baostock")
                break


        return cyq_data













if __name__ == '__main__':
    # Stock_Info.get_stocks_info("use")
    # Stock_Info.my_stock_from_excel()
    # Stock_Info.get_realtime_data('002240')
    # Stock_Info.get_financial_data('002258')
    # Stock_Info.get_capital_flow('002258')
    # Stock_Info.get_historical_high('002258')
    # print(Stock_Info.get_fund_flowInfo(stock_list=['603019','002249']))
    # 获取今日个股资金流排名数据
    # stock_history_fund = ak.stock_individual_fund_flow('603019')
    # df_rank_today = ak.stock_individual_fund_flow_rank(indicator="今日")
    # print("今日个股资金流排名数据：", df_rank_today)

    # print(f"今日实时数据：", Stock_Info.get_realtime_data('002240'))
    # Stock_Info.get_realtime_data(['601212','002240','600362','002471'])
    # # 筛选出股票代码为 '002249' 的数据
    # df_002249 = df_rank_today[df_rank_today['代码'] == '002249']
    # # 打印筛选结果
    # print(df_002249)
    # Stock_Info.get_stocks_list_flowInfo(['002126', '600111'])
    # df = ak.stock_zh_a_daily(symbol="sz000001", start_date="20250601", end_date="20251101",adjust="qfq")
    # df = ak.stock_zh_a_hist(symbol="002240", period="daily", start_date="20250101", end_date='20251001',adjust="")
    # print(df)
    # df = ak.stock_zh_a_hist('002240', '20250101', '20251001')
    # df = ak.stock_zh_a_spot_em()

    # print(Stock_Info.get_stocks_info(stockType='myStock'))
    pass
