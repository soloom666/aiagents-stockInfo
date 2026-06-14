import tushare as ts
import pandas as pd



token = "441f8995667a55e237cc0d6d700e62d50291b1e8a52eb22eb9454436"
ts.set_token(token)
pro = ts.pro_api()



index_data = pro.index_daily(ts_code="000698.SH", start_date="20210101", end_date="20231231")
index_data.to_csv("000698.SH.csv", index=False)

index_data = pd.read_csv("000698.SH.csv")

index_data['trade_date'] = pd.to_datetime(index_data['trade_date'], format= "%Y%m%d")

index_data.sort_values(by="trade_date", ascending=True, inplace=True)

index_data['next_close'] = index_data['close'].shift(-3)
index_data['return'] = (index_data['next_close'] - index_data['close']) / index_data['close']


index_data.dropna(inplace=True)

import graphviz
from scipy.stats import rankdata
from gplearn.functions import make_function
from gplearn.genetic import SymbolicTransformer
from gplearn.fitness import make_fitness
import numpy as np


init_function = ["add", "sub", "mul", "div", "sqrt", "log", "abs", "neg", "inv", "max", "min"]

# 自定义度量函数，用于评估生成的表达式的性能
def _my_metric(y, y_pred, w):
    # 这里的性能度量是预测值和真实值之和
    value = np.sum(y + y_pred)
    return value
# 创建一个适应度函数，用于基因编程过程中的优化
my_metric = make_fitness(function=_my_metric, greater_is_better=True)

# 数据字段，这些字段是金融数据中常见的列
fields = ['open', 'high', 'low', 'close', 'pre_close','amount']
data = index_data[fields].values  # 从数据集中提取这些字段的值
target = index_data['return'].values  # 目标列，通常是预测的对象，如股票回报

test_size = 0.2  # 测试数据集的比例
test_num = int(len(data) * test_size)  # 测试集的数量
# 划分训练数据和测试数据
X_train = data[:-test_num]
X_test = data[-test_num:]
y_train = np.nan_to_num(target[:-test_num])
y_test = np.nan_to_num(target[-test_num:])

generations = 1000  # 基因编程的迭代次数
function_set = init_function  # 函数集合
metric = my_metric  # 使用自定义的度量标准
population_size = 100  # 种群大小
random_state = 1  # 随机种子，确保结果可以复现
# 初始化SymbolicTransformer，用于执行基因编程
est_gp = SymbolicTransformer(feature_names=fields,
                             function_set=function_set,
                             generations=generations,
                             metric=metric,
                             population_size=population_size,
                             tournament_size=20,
                             random_state=random_state,

                             )

est_gp.fit(X_train, y_train)



[sub(add(neg(low), mul(amount, pre_close)), open),
 div(-0.551, -0.048),
 max(neg(div(abs(sqrt(sub(close, pre_close))), mul(log(add(high, close)), abs(abs(pre_close))))), add(log(add(abs(sub(close, open)), min(log(high), min(high, -0.179)))), div(max(mul(sqrt(-0.112), inv(close)), sqrt(log(close))), add(log(div(high, -0.567)), sub(max(amount, low), min(low, low)))))),
 max(log(div(sqrt(neg(log(pre_close))), sub(sub(min(high, open), div(0.833, open)), sqrt(mul(low, open))))), log(sqrt(sqrt(add(add(0.431, -0.190), sub(0.012, close)))))),
 sqrt(mul(inv(log(abs(log(0.706)))), inv(mul(neg(abs(-0.335)), abs(div(close, high)))))),
 inv(sub(open, close)),
 div(div(mul(neg(div(pre_close, amount)), add(max(0.832, low), neg(open))), sqrt(log(mul(high, 0.070)))), sqrt(abs(div(div(open, high), sub(pre_close, high))))),
 neg(max(neg(add(max(abs(high), mul(pre_close, 0.128)), max(neg(open), log(pre_close)))), min(add(min(sub(pre_close, pre_close), abs(0.542)), inv(inv(close))), div(neg(max(-0.943, high)), sub(mul(pre_close, low), mul(pre_close, amount)))))),
 log(div(low, close)),
 mul(inv(add(sqrt(add(log(amount), sub(low, high))), abs(abs(sub(open, open))))), min(neg(inv(min(max(low, low), neg(-0.013)))), div(log(sub(min(low, 0.342), div(high, pre_close))), min(abs(min(0.523, pre_close)), div(max(amount, pre_close), neg(close))))))]

# 获取训练过程中最佳的程序
best_programs = est_gp._best_programs
best_programs_dict = {}
for p in best_programs:
    # 为每个程序创建一个名称并存储相关信息
    factor_name = 'alpha_' + str(best_programs.index(p))
    best_programs_dict[factor_name] = {'fitness': p.fitness_, 'expression': str(p), 'depth': p.depth_,
                                       'length': p.length_}

# 将程序信息转换为DataFrame并排序
result_df = pd.DataFrame(best_programs_dict).T  # 转置之后能更容易可视化分析
result_df.sort_values(by="fitness", ascending=False, inplace=True)


# 定义一个函数，用于可视化选定程序的结构
def alpha_factor_graph(num):
    factor = best_programs[num]
    print(factor)
    print('fitness: {0}, depth: {1}, length: {2}'.format(factor.fitness_, factor.depth_, factor.length_))

    dot_data = factor.export_graphviz()
    graph = graphviz.Source(dot_data)
    graph.render('images/alpha_{0}'.format(num), format='png', cleanup=True)

    return graph


graph = alpha_factor_graph(3)
graph