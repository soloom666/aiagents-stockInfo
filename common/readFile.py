import json
import time

import pandas as pd
import os
import yaml
from mcp.server.fastmcp.server import logger
from tushare import new_stocks

BASE_PATH = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))


class ReadFile:

    def getProjectPath(self=None):
        # 获取项目路径
        projectPath = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return projectPath


    def getFilePath_addProjectPath(flieShortPath):
        file_path =BASE_PATH + flieShortPath
        file_path.replace('\\', '/')
        return file_path


    def getFilePath(flieShortPath, fileName):
        file_path = os.path.join(ReadFile.getProjectPath(), flieShortPath, fileName)
        file_path.replace('\\', '/')
        return file_path


    def read_json(file_path_name=getProjectPath() + '\\config\\config.json'):
        with open(file_path_name, encoding='utf-8') as f:
            com = f.read()
        confJson = json.loads(com)
        return confJson


    def read_file(file_path, file_type='csv', sheet_name='Sheet1'):
        file_path_name = BASE_PATH + file_path
        if file_type=='csv':
            # df=pd.read_csv(file_path_name, encoding='utf-8')
            df = pd.read_csv(file_path_name.replace('\\', '/'), sheet_name=sheet_name, dtype=str, engine='openpyxl')
        elif file_type=='xlsx':
            # df = pd.read_excel(file_path_name, encoding='utf-8')
            df = pd.read_excel(file_path_name.replace('\\', '/'), sheet_name=sheet_name, dtype=str, engine='openpyxl')
        elif file_type=='txt':
            # df = pd.read_table(file_path_name, sep='\t', encoding='utf-8')
            df = pd.read_table(file_path_name, sep=None, encoding='utf-8', engine='python')  # 修改sep参数为None
        return df

    def read_fileNosheet(file_path, file_type='csv'):
        file_path_name = BASE_PATH + file_path
        if file_type=='csv':
            # df=pd.read_csv(file_path_name, encoding='utf-8')
            df = pd.read_csv(file_path_name.replace('\\', '/'), dtype=str, engine='openpyxl')
        elif file_type=='xlsx':
            # df = pd.read_excel(file_path_name, encoding='utf-8')
            df = pd.read_excel(file_path_name.replace('\\', '/'), dtype=str, engine='openpyxl')
        # elif file_type=='xls':
        #     pd.read_excel(file_path_name.replace('\\', '/'), dtype=str)
        elif file_type=='txt':
            # df = pd.read_table(file_path_name, sep='\t', encoding='utf-8')
            df = pd.read_table(file_path_name, sep=None, encoding='utf-8', engine='python')  # 修改sep参数为None
        return df


    def read_stock_list_from_txt(filePath='\\data\\instruments\\A1股自选股.txt'):
        """
        读取txt文件中的股票代码列表
        """
        full_path = BASE_PATH + filePath
        if not os.path.exists(full_path):
            logger.error(f"文件不存在: {full_path}")
            return []
        try:
            with open(full_path, 'r', encoding='utf-8') as file:
                stock_list = [line.strip() for line in file]
            return stock_list
        except Exception as e:
            logger.error(f"读取文件 {full_path} 时发生异常: {e}")
            return []


    def operJson(jsonFilePath, mode, data=None):
        filePath = BASE_PATH + jsonFilePath
        if mode == "w":
            with open(filePath, mode="w", encoding="utf-8") as f:
                f.write(json.dumps(data, indent=4, ensure_ascii=False))  # 缩进4个空格 解决乱码
        elif mode == "a":
            with open(filePath, mode="a", encoding="utf-8") as f:
                f.write(json.dumps(data, indent=4, ensure_ascii=False))
        elif mode == "r":
            with open(filePath, mode="r", encoding="utf-8") as f:
                jsonLoad = json.loads(f.read())
                return jsonLoad
        elif mode == "c":
            logger.info(f"清空文件：{filePath}")
            with open(filePath, mode="w", encoding="utf-8") as f:
                f.write("")
        elif mode == "d":
            logger.info(f"删除文件：{filePath}")
            os.remove(filePath)
        else:
            logger.info(f"输入mode有误：{mode}")


    def replase_json_data(file_path, new_stocks, key='longhuban_stocks'):
        """
        替换 JSON 文件中的 龙虎榜跟主力选股数据
        """
        # 读取现有 JSON 数据
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if key == 'longhuban_stocks' and new_stocks != []:  # 判断是否为空
            # 更新 longhuban_stocks 字段
            longhuban_stocks = [str(stock) for stock in new_stocks]
            data['longhuban_stocks'] = longhuban_stocks
        elif key == 'main_stocks':
            if all(not value for value in new_stocks.values()):
                logger.info("new_stocks['main_stocks'] 字典的所有值都是空,没有需要处理的数据")
                return
            else:
                data['main_stocks'] = new_stocks               # 更新 main_stocks 字段
        else:
            logger.info(f"替换json内容的key有误：{key}")
        data['time'] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        # 写回文件
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"更新json字段内容成功！")


    def initResultExcel(filePath, data=['time','strategy', 'stock','buy_or_sell','price','runResult','推荐结果']):
        #初始化文件
        # filePath = BASE_PATH + filePath
        with pd.ExcelWriter(filePath, mode='w', engine='openpyxl') as writer:
            df = pd.DataFrame(columns=data)
            df.to_excel(writer, sheet_name='Sheet1', index=False)

    def read_yamlAllPath(path_yaml_name):
        data_file_path = ReadFile.getProjectPath() + path_yaml_name
        with open(data_file_path, mode='r', encoding='utf-8') as f:
            fr = f.read()
            data = yaml.load(fr, Loader=yaml.FullLoader)

            return data

    def get_yamlAllPath(pathFileNme):
        if pathFileNme:
            fileDate = ReadFile.read_yamlAllPath(pathFileNme)
        else:
            logger.info(f"数据文件名有误：{pathFileNme}")

        return fileDate

    def appendResultExcel(filePath, datas):
        #追加数据
        df = pd.DataFrame(datas)
        with pd.ExcelWriter(path=filePath, mode='a', if_sheet_exists='overlay') as writer:
                df.to_excel(writer, sheet_name='Sheet1', index=False, header=False, startrow=writer.sheets['Sheet1'].max_row)


    def golden_resultToExcel(context, order, strategy, filePath):
        # 标的代码
        symbol = order['symbol']
        # 委托价格
        price = order['price']
        # 委托数量
        volume = order['volume']
        # 目标仓位
        target_percent = order['target_percent']
        # 查看下单后的委托状态，等于3代表委托全部成交
        status = order['status']
        # 买卖方向，1为买入，2为卖出
        side = order['side']
        # 开平仓类型，1为开仓，2为平仓
        effect = order['position_effect']
        # 委托类型，1为限价委托，2为市价委托
        order_type = order['order_type']
        if status == 3:
            if effect == 1:
                if side == 1:
                    side_effect = '开多仓'
                    buy_or_sell = '买入'
                else:
                    side_effect = '开空仓'
                    buy_or_sell = '卖'
            else:
                if side == 1:
                    side_effect = '平空仓'
                    buy_or_sell = '买入'
                else:
                    side_effect = '平多仓'
                    buy_or_sell = '卖'
            order_type_word = '限价' if order_type == 1 else '市价'
            logger.info(
                f'{context.now}:标的：{symbol}，操作：买卖方向：{buy_or_sell},以{order_type_word}{side_effect}，委托价格：{price}，委托数量：{volume}')

            # 将运行结果写入Excel表
            sock_time = (context.now).strftime('%Y-%m-%d %H:%M:%S')
            return_json = {
                "time": sock_time,
                "strategy": strategy,
                "stock": symbol,
                "buy_or_sell": buy_or_sell,
                "price": price,
                "runResult": order_type_word + side_effect
            }
            df = pd.DataFrame([return_json])
            with pd.ExcelWriter(path=filePath, mode='a', if_sheet_exists='overlay') as writer:
                df.to_excel(writer, sheet_name='Sheet1', index=False, header=False,
                            startrow=writer.sheets['Sheet1'].max_row)


    def golden_jsonStock_resultToExcel(context,strategy,stock,buy_or_sell,result,filePath):
        print('运行结果json写入Excel表')
        sock_time = (context.now).strftime('%Y-%m-%d %H:%M:%S')
        return_json = {
            "time": sock_time,
            "strategy": strategy,
            "stock": stock,
            "buy_or_sell": buy_or_sell,
            "price": '',
            "runResult": result
        }
        df = pd.DataFrame([return_json])
        with pd.ExcelWriter(path=filePath, mode='a', if_sheet_exists='overlay') as writer:
            df.to_excel(writer, sheet_name='Sheet1', index=False, header=False,
                        startrow=writer.sheets['Sheet1'].max_row)


if __name__ == '__main__':
    # ReadFile.getFilePath_addProjectPath("/datas/output/selfChooseStockResult/selfChooseStock.xlsx")
    # longhuban_stocks = ['000221', '600579', '600580', '600581', '600582', '600583']
    # ReadFile.replase_json_data('D:\\D_disk\\project\\code\\pythonCode\\pythonProject\\stockProject\\aitrader\\data\\output\\json\\al_agent_stock_program.json',longhuban_stocks, 'main_stocks')
    pass