import random
from datetime import datetime, timedelta
import logging
import pandas as pd
from common.readFile import ReadFile,BASE_PATH
import akshare as ak
from common.getTime import getDateStr
from common.logger import logger
import time


confJson = ReadFile.read_json()
start_date = confJson['开始时间']
end_date = getDateStr()



def addTwo_stock(stock='600031'):
    #代码前缀拼接两位小写：sh600031
    stock_two = stock[:2].upper()
    if stock_two=='SH' or stock_two=='SZ':
        stock =stock.lower()
    else:
        if stock[:3] in ['110' ,'113' ,'118' ,'510' ,'519',
                         "900" ,'200'] or stock[:2] in ['11' ,'51' ,'60' ,'68'] or stock[:1] in ['5']:
            stock = 'sh' + stock
        else:
            stock ='sz' + stock
    return stock


def sh_or_sz(stock='600031'):
    #代码前缀拼接两位小写：sh600031
    stock_two = stock[:2].upper()
    if stock_two=='SH' or stock_two=='SZ':
        stock =stock.lower()
    else:
        if stock[:3] in ['110' ,'113' ,'118' ,'510' ,'519',
                         "900" ,'200'] or stock[:2] in ['11' ,'51' ,'60' ,'68'] or stock[:1] in ['5']:
            stockType = 'sh'
        else:
            stockType ='sz'
    return stockType


def add_stock(stock='600031'):
    #代码前缀拼接--掘金策略常用-- 同花顺下载的EXCEL
    stock_two = stock[:2].upper()
    if stock_two=='SH':
        stock =stock.replace('SH','SHSE.')
    elif stock_two=='SZ':
        stock =stock.replace('SZ','SZSE.')
    else:
        if stock[:3] in ['110' ,'113' ,'118' ,'510' ,'519',
                         "900" ,'200'] or stock[:2] in ['11' ,'51' ,'60' ,'68'] or stock[:1] in ['5']:
            stock = 'SHSE.' + stock
        else:
            stock ='SZSE.' + stock
    return stock



def add_stockList(stockList=['600031']):
    #list代码前缀拼接--掘金策略常用
    add_stockList =[]
    for i in range(len(stockList)):
        stock = add_stock(stockList[i])
        add_stockList.append(stock)
    return add_stockList

def add_stockList_from_excel(isRemoveSH=False, isGetStockName=False, stockAddType=3, filePath='/aitrader/data/input/Table.xlsx'):
    """
       从Excel读取股票代码, isRemoveSH=True 去掉前两位sh,  isGetStockName=True 获取股票名称
        stockAddType: 1为前缀加两个小写 sh600031，2为后缀加两个大写 600031.SH,
        3为前缀加四个大写 SHSE.600031
    """
    df = ReadFile.read_fileNosheet(filePath,'xlsx')
    add_stockLists = []
    stockNameLists = []
    for index, row in df.iterrows():
        try:
            # stock = row['代码']
            # stockName = row['名称']
            stock = row['股票代码']
            stockName = row['股票简称']
            print(f'读取Excel代码拼接前stock：{stock},isRemoveSH：{isRemoveSH},stockAddType：{stockAddType}')
            if isRemoveSH and (stock[-2:].upper() not in ['SH','SZ']):
                # print(f'去掉前两位sh, stock：{stock},{stock[-2:]}')
                stock = '' + stock[2:]
            if stockAddType==1:
                addStock = addTwo_stock(stock)
            elif stockAddType==2:
                addStock = stock_adjust(stock)
            elif stockAddType==3:
                addStock = add_stock(stock)
            else:
                logging.error(f'addStock传参有误stockAddType：{stockAddType}')
            add_stockLists.append(addStock)
            stockNameLists.append(stockName)
        except Exception as e:
            logging.error(f'读取Excel代码拼接异常：{e}')
    if isGetStockName:
        return add_stockLists, stockNameLists
    else:
        return add_stockLists





def stock_adjust(stock='600031'):
    # 代码后缀拼接 .SH 或 .SZ
    print(f'代码后缀拼接前stock：{stock}')
    stock_two = stock[-2:]
    if stock_two.upper()=='SH' or stock_two.upper()=='SZ':
        stock=stock.upper()
    else:
        if stock[:3] in ['110','113','118','510','519',
                        "900",'200'] or stock[:2] in ['11','51','60','68'] or stock[:1] in ['5']:
            stock=stock+'.SH'
        else:
            stock=stock+'.SZ'
    print(f'代码后缀拼接后stock：{stock}')
    return stock

def excelStock_To_txt(fromfilePath='/aitrader/data/input/Table.xlsx', toFilePath='\\data\\instruments\\A1股自选股.txt'):
    # 将Excel中的股票代码写入平台运行的txt文件
    excel_stocks = add_stockList_from_excel(isRemoveSH=True, stockAddType=2, filePath=fromfilePath)
    with open(BASE_PATH + toFilePath, 'w', encoding='utf-8') as file:
        for stock in excel_stocks:
            # print(stock)
            file.write(stock + '\n')



def get_stock_info(fromfilePath, toFilePath, start_date=start_date, end_date=end_date):
    """
    1、导出的股Excel转成txt， 拼接.SH
    2、读取txt， 获取股票代码日线数据并写入.csv文件
    """
    excelStock_To_txt(fromfilePath,toFilePath)
    txt_stocks = ReadFile.read_stock_list_from_txt(toFilePath)
    if isinstance(txt_stocks, pd.DataFrame):  # 确保 txt_stocks 是一个列表
        txt_stocks = txt_stocks.iloc[:, 0].tolist()
        print(txt_stocks)
    stock_to_csv(txt_stocks)


def stock_to_csv(stockList=['600515.SH','300124.SZ']):
    # 延迟导入，避免循环导入问题
    from a_self_Strategy.untils.stocks_Info import Stock_Info

    #指定某个股生成csv文件
    for stock in stockList:
        if '.' in stock:  # 分割去除后缀，处理可能的分割失败情况
            stock_single = stock.split('.')[0]
        else:
            print(f"警告: {stock} 不包含 '.'，无法正确分割")
            continue

        logger.info(f'分割去除后缀:{stock},stock_single:{stock_single} ,start_date:{start_date}, end_date:{end_date}')
        time.sleep(random.uniform(1, 3))  # 暂停随机时间，避免过快访问
        # 使用 baostock 替代 akshare
        stock_zh_a_hist_df = Stock_Info.get_stock_hist_data(symbol=stock_single, start_date=start_date,
                                                end_date=end_date, period="daily", adjust="")
        print(f"stock_zh_a_hist_df:{stock_zh_a_hist_df}")
        if '日期' in stock_zh_a_hist_df.columns:  # 确保'日期'列存在后再重命名和设置索引
            result = stock_zh_a_hist_df.rename(
                columns={'日期': 'date', '股票代码': 'stock', '开盘': 'open', '最高': 'high', '收盘': 'close',
                         '最低': 'low', '成交量': 'volume'}).set_index('date')
            result['adj_factor'] = 1
            result['symbol'] = stock
            result.to_csv(BASE_PATH + '/aitrader/data/quotes/' + stock + '.csv')  # 写入CSV文件的路径
        else:
            print(f"警告: {stock_zh_a_hist_df} 的数据中没有 '日期' 列,写入有误！！！")


if __name__ == '__main__':
    #Excel数据转TXT，并获取股票信息写入CSV
    get_stock_info(fromfilePath='/aitrader/data/input/myStock/我的自选.xlsx', toFilePath='\\aitrader\\data\\instruments\\A1我的自选.txt')
