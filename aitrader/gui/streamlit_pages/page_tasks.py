import json
from datetime import datetime
from bt_algos_extend import Engine
from common.stockBasic import get_stock_info
from configs import DATA_DIR
import os
import streamlit as st
from common.logger import logger
from tasks import task_list
import pandas as pd



def get_instruments():
    files = os.listdir(DATA_DIR.joinpath('instruments').resolve())
    return files


def build_page():
    tasks = task_list()

    def _format_x(task):
        return task.name

    task_selected = st.multiselect(label='请选择策略(支持同时运行多个策略)', options=tasks, format_func=lambda x: _format_x(x))
    fileStr = st.selectbox(label='选择标的池', options=get_instruments(), index=None)
    #默认为不更新
    updateStckInfoFlag = st.selectbox(label='是否更新数据', options= ['是', '否'], index=None)
    symbols = None
    if fileStr:
        with open(DATA_DIR.joinpath('instruments').joinpath(fileStr).resolve(), 'r') as file:
            lines = file.readlines()

            # 将每行的数据放入列表中
            symbols = [line.strip() for line in lines]
            st.write(symbols)

    if st.button('运行策略'):
        with st.spinner('回测进行中，请稍后...'):
            try:
                if fileStr == "A1我的自选.txt":
                    print("运行策略先更新-自选Stocks的信息")
                    if updateStckInfoFlag == '是':
                        get_stock_info(fromfilePath='/aitrader/data/input/myStock/我的自选.xlsx',toFilePath='/data/instruments/A1我的自选.txt')

                if symbols and len(symbols):
                    for t in task_selected:
                        t.symbols = symbols
                res = Engine().run_tasks(task_selected)

                df = res.stats
                import matplotlib.pyplot as plt
                # plt.title('策略运行结果')
                from matplotlib import rcParams
                rcParams['font.family'] = 'SimHei'
                res.plot()

                st.pyplot(plt.gcf())

                for c in df.columns:
                    st.markdown("<strong><u>{}</u></strong>".format(c), unsafe_allow_html=True)
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric(label="年化收益", value='{}%'.format(round(df.loc['cagr'][c] * 100, 1)))
                    with col2:
                        st.metric(label="最大回撤率", value=str(round(df.loc['max_drawdown'][c] * 100, 1)) + '%')
                    with col3:
                        st.metric(label="卡玛比率", value=str(round(df.loc['calmar'][c], 2)))

                # st.write(res.get_transactions())
                transactions = res.get_transactions()
                if not transactions.empty:
                    st.write(transactions)
                    now = datetime.now()
                    print(f'运行结果：{transactions}')
                    df = pd.DataFrame(transactions)
                    # filtered_excel = df[((df['quantity']> 80) | (df['quantity']< -80))]
                    filtered_excel = df[((df['quantity']> 100))]
                    print(f'filtered_excel:  {filtered_excel}')
                    filtered_excel.to_excel(DATA_DIR.joinpath('output/excel').joinpath(f'{now.strftime("%Y%m%d_%H%M%S")}.xlsx').resolve())
                else:
                    st.info("没有交易记录")
            except Exception as e:
                logger.error(f"Failed to run tasks: {e}")
                st.error(f"Failed to run tasks: {e}")