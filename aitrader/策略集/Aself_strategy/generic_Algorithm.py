import random
from deap import base, creator, tools, algorithms
import numpy as np


# 定义评估函数，用于评估交易策略的表现
def evaluateStrategy(individual):
    # 示例中使用简化的策略评估逻辑，实际应用中应连接到具体的金融数据和交易回测系统
    # 个体的各个部分可以表示不同的交易规则或参数
    period1, period2 = individual
    # 假设这里的period1和period2分别代表两个不同的移动平均线周期
    if period1 > period2:
        simulated_profit = random.uniform(0, 1)  # 模拟一个盈利，实际中应为回测得出的收益
        return simulated_profit,
    else:
        return random.uniform(-1, 0),  # 模拟一个亏损


# 设置遗传算法的基础结构
creator.create("FitnessMax", base.Fitness, weights=(1.0,))  # 寻求最大化问题
creator.create("Individual", list, fitness=creator.FitnessMax)

toolbox = base.Toolbox()
toolbox.register("attr_int", random.randint, 10, 100)  # 交易周期参数在10到100之间
toolbox.register("individual", tools.initRepeat, creator.Individual, toolbox.attr_int, 2)  # 个体由两个参数组成
toolbox.register("population", tools.initRepeat, list, toolbox.individual)

toolbox.register("evaluate", evaluateStrategy)
toolbox.register("mate", tools.cxTwoPoint)  # 交叉算子
toolbox.register("mutate", tools.mutUniformInt, low=10, up=100, indpb=0.1)  # 变异算子，每个基因的变异概率为0.1
toolbox.register("select", tools.selTournament, tournsize=3)  # 选择算子


# 生成初始种群
population = toolbox.population(n=100)  # 种群大小为100


# 应用遗传算法
NGEN = 40  # 进化代数
for gen in range(NGEN):
    offspring = algorithms.varAnd(population, toolbox, cxpb=0.5, mutpb=0.2)  # 交叉概率0.5，变异概率0.2
    fits = map(toolbox.evaluate, offspring)
    for fit, ind in zip(fits, offspring):
        ind.fitness.values = fit
    population = toolbox.select(offspring, len(population))


top10 = tools.selBest(population, k=10)
print("Top 10 strategies:", top10)







