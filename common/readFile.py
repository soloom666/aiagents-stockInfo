import json
import pandas as pd
import os
from datetime import datetime
from common.logger import logger
import yaml



BASE_PATH = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))


class ReadFile:

    def _resolve_path(path_value, base_path=BASE_PATH):
        """Resolve mixed Windows/Linux separators to a project-local absolute path."""
        if path_value is None:
            return os.path.normpath(base_path)

        raw_path = str(path_value).strip()
        if not raw_path:
            return os.path.normpath(base_path)

        normalized = raw_path.replace("\\", "/")
        base_normalized = str(base_path).replace("\\", "/").rstrip("/")
        candidate = os.path.normpath(normalized)

        if normalized == base_normalized or normalized.startswith(base_normalized + "/"):
            return candidate

        is_windows_abs = len(normalized) >= 2 and normalized[1] == ":"
        is_unc_path = normalized.startswith("//")
        if is_windows_abs or is_unc_path:
            return candidate

        project_relative_roots = (
            "/aitrader",
            "/config",
            "/data",
            "/docs",
            "/log",
            "/common",
        )
        if normalized.startswith("/") and not normalized.startswith(project_relative_roots):
            return candidate

        if os.path.isabs(candidate) and os.path.exists(os.path.dirname(candidate)):
            return candidate

        if normalized.startswith("/"):
            return os.path.normpath(os.path.join(base_path, normalized.lstrip("/")))

        return os.path.normpath(os.path.join(base_path, normalized))

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


    def read_json(file_path_name=getProjectPath() + '/config/config.json'):
        file_path_name = ReadFile._resolve_path(file_path_name, ReadFile.getProjectPath())
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


    def read_xls_data(file_path):
            """
            读取 xls 文件中的所有工作表
            """
            file_path_name = BASE_PATH + file_path
            all_sheets = pd.read_excel(file_path_name, sheet_name=None)
            return all_sheets


    def read_fileNosheet(file_path, file_type='csv'):
        file_path_name = BASE_PATH + file_path
        if file_type=='csv':
            # df=pd.read_csv(file_path_name, encoding='utf-8')
            df = pd.read_csv(file_path_name.replace('\\', '/'), dtype=str, engine='openpyxl')
        elif file_type=='xlsx':
            df = pd.read_excel(file_path_name.replace('\\', '/'), dtype=str, engine='openpyxl')
        # elif file_type == 'xls':
        #     df = pd.read_excel(file_path_name.replace('\\', '/'), dtype=str, engine='xlrd')
        elif file_type=='txt':
            # df = pd.read_table(file_path_name, sep='\t', encoding='utf-8')
            df = pd.read_table(file_path_name, sep=None, encoding='utf-8', engine='python')  # 修改sep参数为None
        return df


    def read_stock_list_from_txt(filePath='/data/instruments/A1股自选股.txt'):
        """
        读取txt文件中的股票代码列表
        """
        full_path = ReadFile._resolve_path(filePath, BASE_PATH)
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
        filePath = ReadFile._resolve_path(jsonFilePath, BASE_PATH)
        if mode == "w":
            os.makedirs(os.path.dirname(filePath), exist_ok=True)
            with open(filePath, mode="w", encoding="utf-8") as f:
                f.write(json.dumps(data, indent=4, ensure_ascii=False))  # 缩进4个空格 解决乱码
        elif mode == "a":
            os.makedirs(os.path.dirname(filePath), exist_ok=True)
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


    def initResultExcel(filePath, data=['time','strategy', 'stock','buy_or_sell','price','runResult','推荐结果']):
        #初始化文件
        # filePath = BASE_PATH + filePath
        with pd.ExcelWriter(filePath, mode='w', engine='openpyxl') as writer:
            df = pd.DataFrame(columns=data)
            df.to_excel(writer, sheet_name='Sheet1', index=False)

    def read_yamlAllPath(path_yaml_name):
        data_file_path = ReadFile._resolve_path(path_yaml_name, ReadFile.getProjectPath())
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

    def get_AI_json_stocks(jsonFile= '/aitrader/data/output/json/al_agent_stock_program.json'):
        # 获取json文件所有stocks数据
        al_agent_stocks = ReadFile.operJson(jsonFile, 'r')

        main_stocks = al_agent_stocks['main_stocks']
        main_fundFlow__codes = main_stocks['fund_flow_analysis_codes']
        main_industry_analysis_codes = main_stocks['industry_analysis_codes']
        main_fundamental_analysis_codes = main_stocks['fundamental_analysis_codes']
        longhuban_stocks = al_agent_stocks['longhuban_stocks']

        def _to_list(val):
            """将字符串或其他类型统一转为列表"""
            if isinstance(val, list):
                return val
            if isinstance(val, str):
                return [v.strip() for v in val.split(',') if v.strip()]
            return list(val) if val else []

        # 1、合并并去重所有股票代码
        all_codes = list(dict.fromkeys(
            _to_list(main_fundFlow__codes) +
            _to_list(main_industry_analysis_codes) +
            _to_list(main_fundamental_analysis_codes) +
            _to_list(longhuban_stocks)
        ))
        print(f'合并并去重所有股票代码:{all_codes}')
        return all_codes, al_agent_stocks

    def appendDatasToExcel(datas, filePath='/aitrader/data/input/myStock/我的自选.xlsx', remove_duplicates=True):
        """
        将数据追加到Excel文件的第一列，并去重
        Args:
            datas (list): 要追加的数据列表
            filePath (str): Excel文件路径
            remove_duplicates (bool): 是否去除重复项
        """
        full_path = ReadFile._resolve_path(filePath, BASE_PATH)

        # 检查Excel文件是否存在
        if os.path.exists(full_path):
            # 读取现有Excel数据
            try:
                existing_df = pd.read_excel(full_path)
                # 确保第一列名为'股票代码'
                if existing_df.shape[1] > 0:
                    existing_df.columns = ['股票代码'] + list(existing_df.columns[1:])
                else:
                    existing_df = pd.DataFrame(columns=['股票代码'])
            except Exception as e:
                logger.error(f"读取现有Excel文件失败: {e}")
                existing_df = pd.DataFrame(columns=['股票代码'])
        else:
            # 如果文件不存在，创建新的DataFrame
            existing_df = pd.DataFrame(columns=['股票代码'])

        # 将新数据转换为DataFrame
        if isinstance(datas, list):
            new_df = pd.DataFrame(datas, columns=['股票代码'])
        else:
            new_df = pd.DataFrame([datas], columns=['股票代码'])

        # 合并现有数据和新数据
        combined_df = pd.concat([existing_df, new_df], ignore_index=True)

        if remove_duplicates:
            # 去重，保持顺序
            combined_df = combined_df.drop_duplicates(subset=['股票代码'], keep='first')

        # 保存到Excel文件，确保数据在第一列
        try:
            combined_df.to_excel(full_path, index=False)
            logger.info(f"成功将 {len(new_df)} 条数据追加到 {full_path} 第一列，去重后总数据量: {len(combined_df)}")
        except Exception as e:
            logger.error(f"保存Excel文件失败: {e}")


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



    def replase_json_data(json_file_path, json_data):
        """
        替换JSON文件中的数据
        :param json_file_path: JSON文件路径（完整路径）
        :param json_data: 要替换的数据（dict），只更新其中包含的键
        :return:
        """
        if not isinstance(json_data, dict):
            logger.error(f"json_data 必须是 dict，当前类型: {type(json_data)}")
            return

        json_file_path = ReadFile._resolve_path(json_file_path, ReadFile.getProjectPath())
        os.makedirs(os.path.dirname(json_file_path), exist_ok=True)

        existing_data = {}
        try:
            with open(json_file_path, mode='r', encoding='utf-8') as f:
                existing_data = json.load(f)
                print(f"存在数据：{existing_data}")
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.warning(f"读取JSON文件失败，将创建新文件: {json_file_path}, 错误: {e}")

        if not isinstance(existing_data, dict):
            logger.warning(f"JSON文件内容不是对象结构，已重置: {json_file_path}")
            existing_data = {}

        existing_data.update(json_data)
        existing_data['time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        with open(json_file_path, mode='w', encoding='utf-8') as f:
            f.write(json.dumps(existing_data, indent=4, ensure_ascii=False))

        print(f"JSON文件已更新：{json_file_path}")
        print(f"更新后数据：{existing_data}")





if __name__ == '__main__':
    # ReadFile.getFilePath_addProjectPath("/aitrader/datas/output/selfChooseStockResult/selfChooseStock.xlsx")

    longhuban_stocks = { "longhuban_stocks": [
        "002566",
        "600986"
    ]
    }



    ReadFile.replase_json_data(
        '/aitrader/data/output/json/al_agent_stock_program.json', longhuban_stocks)
