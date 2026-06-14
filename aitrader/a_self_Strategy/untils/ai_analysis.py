import json
import random
import re
import time
from openai import OpenAI
import akshare as ak
import pandas as pd
from aitrader.a_self_Strategy.untils.stocks_Info import Stock_Info
from common.logger import logger
from common.readFile import ReadFile
# from concurrent.futures import ThreadPoolExecutor




# stock_code = Stock_Info.get_stocks_info('use')
confJson = ReadFile.read_json()
DEEPSEEK_API_KEY = confJson['deepseek_api_key']
BASE_URL = confJson['base_url']
client = OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url=BASE_URL
)


#一、数据合并（数据层）
def merge_data(stock_code):
    print("merge_data的stock_code：", stock_code)
    realtime_df = Stock_Info.get_realtime_data(stock_code)
    financial_df = Stock_Info.get_financial_data(stock_code)
    capital_df = Stock_Info.get_capital_flow(stock_code)
    print(f"realtime_df：\n {realtime_df}\n, financial_df:\n {financial_df},\ncapital_df:\n {capital_df}")
    df = pd.concat([
        realtime_df.reset_index(drop=True),
        financial_df.reset_index(drop=True),
        capital_df.reset_index(drop=True)
    ], axis=1)

    # 删除包含 NaN 的行
    df = df.dropna()
    # df = pd.concat([realtime_df.reset_index(drop=True), financial_df.reset_index(drop=True), capital_df.reset_index(drop=True)], axis=1)
    print("合并后的数据列表：\n", df.columns.tolist())
    print("合并后的数据：\n", df)
    return df



# 二、DeepSeek智能分析（模型层）
# 2.1 多维度分析提示词
def build_analysis_prompt(stock_data):
    return f"""
    作为专业股票分析师，请根据以下数据对{stock_data['名称']}({stock_data['代码']})进行评分(0-10星)：

    【基本面】
    - 最新价：{stock_data['最新价']}元
    - 市盈率-动态：{stock_data['市盈率-动态']}（行业平均：25）
    - 市净率：{stock_data['市净率']}（行业平均：2.5）
    - 市净率：{stock_data['净资产收益率']}（行业优秀：15%）

    【技术面】
    - 涨跌幅：{stock_data['涨跌幅']}%
    - 5分钟涨跌：{stock_data['5分钟涨跌']}%
    - 量比：{stock_data['量比']}

    【资金面】
    - 主力净流入：{stock_data['主力净流入-净额']}元
    - 超大单净流入：{stock_data['超大单净流入-净额']}元
    - 大单净流入：{stock_data['大单净流入-净额']}元
    - 中单净流入：{stock_data['中单净流入-净额']}元
    - 小单净流入：{stock_data['小单净流入-净额']}元


    评分标准：
    1. 盈利能力(ROE>10% +2星)
    2. 估值水平(PE<30且PB<3 +1星)
    3. 资金热度(主力连续3日净流入 +2星)
    4. 技术形态(量价齐升 +3星)
    5. 行业地位(细分龙头 +2星)

    最终评分建议需包含：
    - 星级评价与理由
    - 关键风险提示
    - 短期操作建议
    
    """



# 2.2 多模型协同分析
# def deepseek_analyze(prompt):
def deepseek_analyze(prompt, max_retries=3):
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[{
                    "role": "system",
                    "content": """
                    你的核心任务是提供专业、全面、数据驱动且具备前瞻性的股票分析内容。分析时需严格遵循以下要求：
多维度分析融合：必须结合基本面（涵盖公司财务指标、商业模式、行业地位、竞争壁垒、管理层能力、政策影响等）、技术面（包含 K 线形态、均线系统、成交量能、MACD/RSI 等关键指标、支撑压力位等）与市场情绪（涉及资金流向、舆情热度、投资者持仓结构、板块轮动节奏等）三大维度，拒绝单一视角判断。
多因子模型应用：熟练运用多因子模型辅助投资决策，筛选核心因子（如估值因子、成长因子、盈利因子、动量因子、质量因子等），量化评估标的的投资价值与风险系数，给出明确的因子权重分析。
风险提示前置：始终将风险提示放在突出位置，明确指出宏观经济风险、行业政策风险、公司经营风险、市场波动风险等潜在隐患，同时给出对应的风险应对建议，不做绝对性、诱导性结论。
结论清晰可落地：最终输出的分析报告需逻辑严谨、论据充分，明确给出投资评级（如买入、持有、卖出）、目标价位区间（如有数据支撑）及投资周期建议，兼顾专业深度与实操性。
"""
                },{
                    "role": "user",
                    "content": prompt
                }],
                temperature=0.3,
                max_tokens=1500
            )
            # return response.choices[0].message.content
            content = response.choices[0].message.content
            if content and len(content.strip()) > 0:
                return content
        except Exception as e:
            logger.warning(f"API调用第{attempt + 1}次失败: {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # 指数退避

        logger.error("API调用达到最大重试次数仍失败")
        return None




# 三、分析结果结构化（应用层）
# 3.1 自动化评分系统
def auto_scoring(stock_code):
    data = merge_data(stock_code).iloc[0]
    prompt = build_analysis_prompt(data)
    analysis_result = deepseek_analyze(prompt)

    return {
        "股票代码": stock_code,
        "股票名称": data['名称'],
        "综合评分": extract_stars(analysis_result),  # 正则提取星级
        "关键指标": {
            "ROE": data['净资产收益率'],
            "PE": data['市盈率-动态'],
            "主力资金": data['主力净流入-净额']
        },
        "AI分析摘要": analysis_result
    }


def extract_stars(analysis_text):
    """
    从AI分析结果中提取星级评分（如 ★★★★☆）
    :param analysis_text: AI返回的文本内容
    :return: 星级评分（0-10），如果没有匹配则返回0
    """
    if not isinstance(analysis_text, str):
        return 0

    # 匹配中文星号（★）组成的评分，最多10个
    stars_match = re.search(r'(\★{0,10})', analysis_text)

    if stars_match:
        return len(stars_match.group(1))  # 返回星号数量作为评分
    return 0



# 情绪因子集成：集成东方财富股吧情绪分析
def get_sentiment(stock_code):
    return ak.stock_comment_em(stock=stock_code)['情感分值']

# 机构行为追踪
def track_institution(stock_code):
    return ak.stock_institution_hold_detail(stock=stock_code)

# 风险控制
def risk_check(stock_data):
    if stock_data['市盈率'] > 50:
        return "高估值风险警告"
    if stock_data['大单净流入'] < -1000:
        return "主力出逃风险"


# 测试单股AI分析
def signal_stock_analysis(stock_code, jsonFlag=''):
    # realtime = Stock_Info.get_realtime_data(stock_code)
    # financial = Stock_Info.get_financial_data(stock_code)
    # capital = Stock_Info.get_capital_flow(stock_code)
    print("signal_stock_analysis股票代码：", stock_code)
    df = merge_data(stock_code)
    print("合并后的数据：", df)
    if not df.empty:
        result = auto_scoring(stock_code)
        json_output = json.dumps(result, ensure_ascii=False, indent=4)  # 输出 JSON 格式字符串
        logger.info(f"AI 单股分析结果 json_output：{json_output}")  #单股AI分析结果
        if jsonFlag:
            ReadFile.operJson("/aitrader/data/output/json/AI_analysis_result.json", "w", json_output)
        else:
            print(f"个股分析结果不写入json文件：{jsonFlag}")
            return json_output
    else:
        logger.info("数据为空，跳过评分")


#多股分析
def multiple_analyze(stock_list):
    ai_result = []
    # stock_list = Stock_Info.get_stocks_info("use")
    for stock_code in stock_list:
        round(random.uniform(0, 2), 1)  #  随机休眠 0 到 1 秒 , 反限制IP
        stock_analysis = signal_stock_analysis(stock_code,jsonFlag=False)
        ai_result.append(stock_analysis)
        # time.sleep(random.randint(0, 2))  #  随机休眠 0 到 2 秒 , 反限制IP
    json_output = json.dumps(ai_result, ensure_ascii=False, indent=4)  # 输出 JSON 格式字符串
    logger.info(f"多股分析结果：\n{json_output}")



if __name__ == '__main__':
    # stock_list = Stock_Info.get_stocks_info("use")
    stock_list =  ['600079']
    # signal_stock_analysis()
    multiple_analyze(stock_list)