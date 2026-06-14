import tushare as ts
# import pandas as pd
from common.readFile import ReadFile
from datetime import datetime
import requests
import akshare as ak
from common.logger import logger
import asyncio
import platform


now_date = datetime.now().strftime('%Y%m%d')


# 修复 Windows 下 aiodns 报错问题
if platform.system() == "Windows":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

class Fundamentals_risk:
    """
    1、获取当日主力资金净入>600万的股票
    2、获取当日热门行业板块数据
    3、消息面利好  TODO
    4、财务良好 ROE(净资产收益率)>15%
    5、市盈率少于50
    """

    def get_big_dealers(trade_date=now_date):
        """
        获取当日主力资金净入>600万的股票
        """
        # 1. 设置Token 需要积分
        confJson = ReadFile.read_json()
        tushareTken = confJson['tushare_token']
        print(f'tushareTken:{tushareTken},trade_date:{trade_date}')
        # ts.set_token('441f8995667a55e237cc0d6d700e62d50291b1e8a52eb22eb9454436')
        ts.set_token(tushareTken)
        pro = ts.pro_api()
        # 2. 获取当日主力资金数据（含大单交易）
        # df = pro.moneyflow(trade_date='20250526', fields='ts_code,trade_date,buy_lg_amount,sell_lg_amount')  # 字段说明见[1,6](@ref)
        df = pro.moneyflow(trade_date=now_date, fields='ts_code,trade_date,buy_lg_amount,sell_lg_amount')  # 字段说明见[1,6](@ref)
        # 3. 计算大单净流入（单位：万元）
        df['净流入'] = df['buy_lg_amount'] - df['sell_lg_amount']
        # 4. 筛选净流入>600万的股票
        result = df[df['净流入'] > 600].sort_values('净流入', ascending=False)
        # 5. 保存结果
        result.to_excel('大单净流入_20250526.xlsx', index=False)



    def hot_stock_mode(trade_date=now_date):
        """
        获取当日热门行业板块数据
        """
        print(f"当前日期:{trade_date} ")
        # sector_flow = ak.stock_fund_flow_industry(date=trade_date)
        sector_flow = ak.stock_fund_flow_industry()
        # 筛选涨幅前五的热门板块
        hot_sectors = sector_flow.sort_values(by="行业-涨跌幅", ascending=False).head(5)
        logger.info(f"当前日期:{trade_date}--热门板块（按涨幅排序）：")
        print(hot_sectors[["行业", "行业-涨跌幅", "流入资金", "净额"]])
        print(hot_sectors)




    def parse_policy_news(self):
        # 示例：解析政府网站政策公告（需替换实际URL）
        # TODO
        pass

    def get_financial_excellent(symbol='002040', start_year='2020'):
        """
        获取财务良好 ROE(净资产收益率)>15% 的优质股
        """
        # 获取最新财务数据
        stock_financial = ak.stock_financial_analysis_indicator(symbol=symbol, start_year=start_year)
        print(f"获取 {start_year}")
        print(stock_financial)
        # 筛选ROE>15%且连续三年达标
        roe_condition = (
                (stock_financial["roe"] > 15) &  # 修改键名为正确的字段名
                (stock_financial["roe_last_year"] > 15) &  # 修改键名为正确的字段名
                (stock_financial["roe_two_years_ago"] > 15)  # 修改键名为正确的字段名
        )
        high_roe_stocks = stock_financial[roe_condition][["股票代码", "股票简称", "roe"]]  # 修改键名为正确的字段名
        print("ROE>15%的优质股：")
        print(high_roe_stocks.head(10))


    def get_pe_less_than_50(self):
        """
        获取 市盈率少于50 市净率<3，剔除st 的优质股
        """
        stock_spot = ak.stock_zh_a_spot_em()
        # 检查是否有正确列名
        print("可用字段：", stock_spot.columns.tolist())
        #可用字段： ['序号', '代码', '名称', '最新价', '涨跌幅', '涨跌额', '成交量', '成交额', '振幅', '最高', '最低', '今开', '昨收', '量比', '换手率', '市盈率-动态', '市净率', '总市值', '流通市值', '涨速', '5分钟涨跌', '60日涨跌幅', '年初至今涨跌幅']

        required_columns = ['代码', '名称', '市盈率-动态', '市净率', '最新价', '涨跌幅', '成交量']
        missing_columns = [col for col in required_columns if col not in stock_spot.columns]
        if missing_columns:
            raise ValueError(f"缺失必要字段: {missing_columns}")

        quality_stock_condition = (
                (stock_spot['市盈率-动态'] > 0) &
                (stock_spot['市盈率-动态'] < 50) &
                (stock_spot['市净率'] < 3) &
                (~stock_spot["名称"].str.contains("ST")) &
                (~stock_spot['代码'].str.startswith(('30', '688', '8')))  # 排除创业跟科创板 北交所‘8’开头
        )

        filtered_stocks = stock_spot[quality_stock_condition][required_columns]
        logger.info("市盈率<50的股票,市净率<3，剔除st 的优质股：")
        print(filtered_stocks)
        return filtered_stocks



if __name__ == '__main__':
    # Fundamentals_risk().hot_stock_mode()
    # Fundamentals_risk().get_financial_excellent()
    Fundamentals_risk().get_pe_less_than_50()
    # print(Fundamentals_risk().get_financial_excellent())

