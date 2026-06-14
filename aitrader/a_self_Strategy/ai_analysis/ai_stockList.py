from aitrader.a_self_Strategy.untils.ai_analysis import multiple_analyze


def  ai_analysis_stockList(stock_list):
    multiple_analyze(stock_list)



if __name__ == '__main__':
    stock_list= ['600362','600097','600410','002155','600489']
    ai_analysis_stockList(stock_list)


