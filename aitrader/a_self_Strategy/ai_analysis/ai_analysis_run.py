import sys
import os

# 获取项目根目录（aitrader目录）
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..', '..'))
sys.path.insert(0, project_root)

# 初始化 akshare 代理配置（防止 IP 被封）
from aitrader.common.proxy_config import ProxyConfig
ProxyConfig.init_akshare_proxy()

from aitrader.a_self_Strategy.strategy.al_yaogu import yaogu_qibao_test
from aitrader.a_self_Strategy.strategy.macd_boll import macd_boll_test
from aitrader.a_self_Strategy.strategy.monsterHunting import common_strategy_screening
from aitrader.a_self_Strategy.strategy.yaogu_backtest import run_backtest
from aitrader.a_self_Strategy.untils.ai_analysis import multiple_analyze
from aitrader.a_self_Strategy.untils.stocks_Info import Stock_Info
from common.logger import logger
from aitrader.common.emailSendFiles import emailSendParameter
from common.readFile import ReadFile
from xunlong_self_healing_service import XunlongSelfHealingService

class AiAnalysis:
    def ai_analysis_stock(analyze_type,  stockType=6, riseRate=2):
        """
        1、macd 获取票
        2、Ai 分析票
        stockType = 1 我的自选，2 可操作，3 所有，4 市盈率<50 优秀股
        """
        if stockType == 1:
            stock_list = Stock_Info.my_stock_from_excel()
        elif stockType == 2:
            stock_list = Stock_Info.get_stocks_info('use')
        # elif  stockType == 3:  #  所有的数据太多会被监控系统拒绝 connection without response
        #     stock_list = Stock_Info.get_stocks_info('all')
        elif  stockType == 4:
            stock_list = Stock_Info.get_stocks_info('pe')
        else:
            print('stockType 默认自选股')
            stock_list = Stock_Info.my_stock_from_excel()

        #  多个策略分析macd,妖股 ，默认混合策略
        if analyze_type=='macd':
            ai_stocks_list = macd_boll_test(stock_list=stock_list)  #macd_boll筛选指定股分析
        elif analyze_type=='monster':
            ai_stocks_list = common_strategy_screening(stock_list=stock_list, riseRate=riseRate)
        else:
            ai_macd_stocks = macd_boll_test(stock_list=stock_list)
            ai_common_stocks = common_strategy_screening(stock_list=stock_list, riseRate=riseRate)
            ai_stocks_list = list(set(ai_macd_stocks + ai_common_stocks))
            logger.info(f'最终macd股ai_macd_stocks：{ai_macd_stocks}，\n 涨幅获取股ai_common_stocks:{ai_common_stocks}')
            logger.info(f'macd跟涨幅获取股结果合并--ai_stocks_list:{ai_stocks_list}')
        # multiple_analyze(ai_stocks_list)   # 先不ai分析，汇总挑选后统一再分析
        # return ai_stocks_list
        return ai_stocks_list


    def ai_yaogu_qibao_analysis(stock_list=''):
        """
        妖股分析:stock_list为空时，默认获取我的自选股
        """
        yaogu_stock_list = yaogu_qibao_test(stock_list)
        multiple_analyze(yaogu_stock_list)



    def ai_analysis_stockList(stock_list=''):
        stock_list = ['603215','002249']
        multiple_analyze(stock_list)


    def xunlong(resultJson='/aitrader/data/output/json/recommend_stocks.json', data_source='自选', fast_mode=False):
        """
           1、读取json数据
           2、追加到Excel文件
           3、返回推荐股票数据
           """
        self_healing_service = XunlongSelfHealingService()
        ai_json_all_codes, al_agent_stocks = ReadFile.get_AI_json_stocks()
        ReadFile.appendDatasToExcel(datas=ai_json_all_codes)

        Stock_Info.set_fast_mode(fast_mode)

        ai_macd_stocks = macd_boll_test(
            stock_list=Stock_Info.my_stock_from_excel(),
            fast_mode=fast_mode
        )
        print(f'ai_macd_stocks:{ai_macd_stocks}')
        al_yaogu_stocks = yaogu_qibao_test()
        print(f'al_yaogu_stocyaogu_qibao_testks:{al_yaogu_stocks}')
        # multiple_analyze(al_yaogu_stocks)

        recommend_stocks = {
            'macd': ai_macd_stocks,
            'yaogu': al_yaogu_stocks,
            'al_agent_stocks': al_agent_stocks
        }

        recommend_stocks = self_healing_service.reorder_recommendations(recommend_stocks)

        recommend_stocks_json = ReadFile.operJson(resultJson, 'r')
        if recommend_stocks_json:
            if recommend_stocks != recommend_stocks_json:
                recommend_stocks_diff = set(recommend_stocks['yaogu']).difference(recommend_stocks_json['yaogu'])
                logger.info(f'推荐有变化--recommend_stocks_diff:{recommend_stocks_diff}')
                recommend_stocks['diff'] = list(recommend_stocks_diff)
                logger.info(f'推荐有变化后合并--recommend_stocks:{recommend_stocks}')
                ReadFile.operJson(resultJson, 'w', recommend_stocks)
                if recommend_stocks['diff']:
                    # recommend_stocks['al_agent_stocks'] = al_agent_stocks
                    emailSendParameter(recommend_stocks)
            else:
                logger.info(f'推荐无变化:{recommend_stocks}')

        try:
            batch_id = self_healing_service.record_recommendation_batch(recommend_stocks, data_source=data_source)
            recommend_stocks['batch_id'] = batch_id
        except Exception as exc:
            logger.warning(f'记录寻龙记自愈批次失败: {exc}')
        finally:
            Stock_Info.set_fast_mode(False)

        # 返回推荐股票数据供页面展示
        return recommend_stocks

        # 妖策略回测
        # stock_list = Stock_Info.my_stock_from_excel()
        # for stock_code in stock_list:
        #     analysis = run_backtest(stock_code)
        #     if analysis:
        #         # 使用get方法设置默认值防止KeyError
        #         total_return = analysis['returns'].get('total', 0)
        #         annualized_return = analysis['returns'].get('rnorm100', 0)
        #         logger.info(f"回测结果分析 - 股票: {stock_code}")
        #         logger.info(f"夏普比率: {analysis['sharpe_ratio']['sharperatio']}")
        #         logger.info(f"年化收益率: {annualized_return:.2%}")
        #         logger.info(f"最大回撤: {analysis['drawdown']['max']['drawdown']:.2%}")


if __name__ == '__main__':
    AiAnalysis.xunlong()
