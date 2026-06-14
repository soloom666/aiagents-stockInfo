import re
import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup
from common.logger import logger




now_date = datetime.now().strftime('%Y%m%d')

def get_policy_benefit_stocks(days=3):
    """
    官方公告解析法（核心方案）：获取最近N天含利好关键词的个股公告
    """
    # 获取所有公告数据（默认返回最新公告）
    df = ak.stock_notice_report()

    if df.empty:
        print("未获取到公告数据")
        return pd.DataFrame()

    # 转换公告日期为 datetime 类型
    df['公告日期'] = pd.to_datetime(df['公告日期'], errors='coerce')

    # 计算目标时间段
    today = datetime.now()
    start_date = today - timedelta(days=days)

    # 按日期筛选
    date_mask = (df['公告日期'] >= start_date) & (df['公告日期'] <= today)

    # 定义利好关键词并构建正则表达式（转义特殊字符）
    keywords = ["中标", "战略合作", "增持", "产品获批", "政策支持", "订单突破", "人工智能芯片", "新能源汽车补贴", "5G基建", "绿色金融"]
    pattern = '|'.join(map(re.escape, keywords))

    # 关键词匹配
    title_mask = df['公告标题'].str.contains(pattern, case=False, na=False)

    # 组合条件筛选
    filtered_df = df[date_mask & title_mask]
    print("可用字段：", filtered_df.columns.tolist())

    # 返回需要的字段
    return filtered_df[['代码', '名称', '公告标题', '公告日期', '网址']]


def get_eastmoney_news():
    """
    使用 akshare 获取东方财富个股新闻（推荐方式）
    """
    df = ak.stock_news_em()
    print("可用字段：", df.columns.tolist())
    print(df)
    # 定义利好关键词
    keywords = ["中标", "战略合作", "增持", "产品获批", "政策支持", "订单突破"]
    pattern = '|'.join(map(re.escape, keywords))

    # 筛选含关键词的新闻标题
    mask = df['新闻标题'].str.contains(pattern, case=False, na=False)

    # return df[mask][['新闻标题', '发布时间']]
    return df[mask][['关键词', '新闻标题', '发布时间', '文章来源', '新闻链接']]


# 全局利好关键词（可动态加载）
BENEFIT_KEYWORDS = [
    "中标", "战略合作", "增持", "产品获批", "政策支持", "订单突破",
    "人工智能芯片", "新能源汽车补贴", "5G基建", "绿色金融"
]


def get_policy_benefit_stocks(days=3):
    """
    获取最近N天含利好关键词的个股公告
    """
    try:
        # 每次调用都获取最新日期
        now_date = datetime.now().strftime("%Y%m%d")
        df = ak.stock_notice_report(date=now_date)

        if df.empty:
            logger.warning("未获取到公告数据")
            return pd.DataFrame()

        # 转换公告日期并筛选时间范围
        df['公告日期'] = pd.to_datetime(df['公告日期'], errors='coerce')
        today = datetime.now()
        start_date = today - timedelta(days=days)
        date_mask = (df['公告日期'] >= start_date) & (df['公告日期'] <= today)

        # 构建关键词模式并匹配
        pattern = '|'.join(map(re.escape, BENEFIT_KEYWORDS))
        title_mask = df['公告标题'].str.contains(pattern, case=False, na=False)

        # 组合条件并返回所需字段
        required_cols = ['代码', '名称', '公告标题', '公告日期', '网址']
        available_cols = [col for col in required_cols if col in df.columns]

        return df[date_mask & title_mask][available_cols]

    except Exception as e:
        logger.error(f"获取公告数据失败: {e}")
        return pd.DataFrame()


def get_eastmoney_news(symbol=None):
    """
    获取东方财富个股新闻并筛选利好信息
    :param symbol: 股票代码（可选），若提供则仅返回该股相关新闻
    """
    try:
        df = ak.stock_news_em(symbol=symbol)
        if df.empty:
            logger.warning("未获取到新闻数据")
            return pd.DataFrame()

        # 构建关键词模式并匹配
        pattern = '|'.join(map(re.escape, BENEFIT_KEYWORDS))
        mask = df['新闻标题'].str.contains(pattern, case=False, na=False)

        # 返回所需字段
        required_cols = ['关键词', '新闻标题', '发布时间', '文章来源', '新闻链接']
        available_cols = [col for col in required_cols if col in df.columns]

        return df[mask][available_cols]

    except Exception as e:
        logger.error(f"获取新闻数据失败: {e}")
        return pd.DataFrame()


if __name__ == '__main__':
    # 示例1：获取近3天内利好公告
    print("——— 最近利好公告 ———")
    announcement_df = get_policy_benefit_stocks(days=3)
    print(announcement_df.head())

    # 示例2：获取某只股票相关的利好新闻
    print("\n——— 002040 相关利好新闻 ———")
    news_df = get_eastmoney_news(symbol='002040')
    print(news_df.head())