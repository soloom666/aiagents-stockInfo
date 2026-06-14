# AKShare 数据获取替换方案

## 问题描述
项目中 `ak.stock_zh_a_hist` 无法获取数据，需要使用其他方法替代。

## 解决方案
使用 **baostock** 替代 akshare，已在项目中创建统一的数据获取函数。

## 已完成的修改

### 1. 创建替代函数
在 `a_self_Strategy/untils/stocks_Info.py` 中添加了新的静态方法：
```python
Stock_Info.get_stock_hist_data(symbol, start_date, end_date, period="daily", adjust="")
```

**特点：**
- 使用 baostock 作为数据源（免费、稳定）
- 保持与 akshare 相同的参数和返回格式
- 自动处理股票代码前缀（sh/sz）
- 支持复权选项：""不复权、"qfq"前复权、"hfq"后复权
- 返回的 DataFrame 列名与 akshare 保持一致

### 2. 已更新的文件（全部完成 ✅）

- ✅ `a_self_Strategy/untils/stocks_Info.py`
  - 添加 `get_stock_hist_data()` 函数
  - 更新 `get_historical_high()` 函数
  - 更新 `get_stock_history()` 函数

- ✅ `a_self_Strategy/strategy/macd_boll.py`
  - 第98行：`macd_boll()` 函数中的数据获取
  - 第332行：测试代码

- ✅ `a_self_Strategy/strategy/macd_boll_backtest.py`
  - 第55行：回测代码中的数据获取

- ✅ `a_self_Strategy/strategy/yaogu_backtest.py`
  - 第278行：妖股回测策略

- ✅ `a_self_Strategy/strategy/al_yaogu.py`
  - 第47行：AI妖股策略（后复权）

- ✅ `a_self_Strategy/strategy/monsterHunting.py`
  - 第190行：妖怪猎手策略

- ✅ `A_Share_investment_Agent/src/main.py`
  - 第301行：首次获取历史数据（前复权）
  - 第323行：备用数据获取（前复权）

- ✅ `common/stockBasic.py`
  - 第160行：基础股票数据获取

- ✅ `A_Share_investment_Agent/src/tools/api.py`
  - 第367行：API工具函数

## 使用方法

### 替换前（akshare）：
```python
df = ak.stock_zh_a_hist(
    symbol='000001',
    start_date='20240101',
    end_date='20240630',
    period="daily",
    adjust=""
)
```

### 替换后（baostock）：
```python
df = Stock_Info.get_stock_hist_data(
    symbol='000001',
    start_date='20240101',
    end_date='20240630',
    period="daily",
    adjust=""
)
```

## 其他替代方案对比

| 数据源 | 优点 | 缺点 | 推荐度 |
|-------|------|------|--------|
| **baostock** | 免费、稳定、无需注册 | 数据更新略慢 | ⭐⭐⭐⭐⭐ |
| tushare | 数据全面、更新快 | 需要积分、有调用限制 | ⭐⭐⭐ |
| efinance | 免费、数据新 | 接口可能变动 | ⭐⭐⭐⭐ |
| yfinance | 国际数据全 | A股数据有限 | ⭐⭐ |

## 注意事项

1. **日期格式**：保持 "YYYYMMDD" 格式（如 "20240101"）
2. **股票代码**：直接使用6位代码（如 "000001"），函数会自动添加 sh/sz 前缀
3. **复权类型**：
   - `adjust=""` - 不复权（默认）
   - `adjust="qfq"` - 前复权
   - `adjust="hfq"` - 后复权

4. **数据列名**：函数已处理列名映射，返回的 DataFrame 与 akshare 格式一致：
   - 日期、股票代码、开盘、最高、最低、收盘、成交量、成交额、换手率

## 测试建议

更新完成后，建议进行以下测试：

1. **测试基本功能**
   ```python
   from a_self_Strategy.untils.stocks_Info import Stock_Info

   # 测试获取数据
   df = Stock_Info.get_stock_hist_data(
       symbol='000001',
       start_date='20240101',
       end_date='20240630',
       period="daily",
       adjust=""
   )
   print(df.head())
   print(df.columns)
   ```

2. **测试各个策略文件**
   - 运行 `macd_boll.py` 测试妖股策略
   - 运行 `macd_boll_backtest.py` 测试回测功能
   - 运行 `yaogu_backtest.py` 测试妖股回测

3. **检查数据完整性**
   - 确认返回的列名正确（日期、开盘、最高、最低、收盘等）
   - 确认数据类型正确（数值列为 float）
   - 确认日期格式正确

## 可能遇到的问题

### 1. 导入错误
如果遇到 `ModuleNotFoundError: No module named 'baostock'`，请安装：
```bash
pip install baostock
```

### 2. 循环导入错误（已修复）
**问题描述：**
```
ImportError: cannot import name 'Stock_Info' from partially initialized module
```

**解决方案：**
- 在 `common/stockBasic.py` 中使用延迟导入
- 将 `Stock_Info` 的导入移到 `stock_to_csv` 函数内部
- 详见：`循环导入问题修复说明.md`

### 3. 数据为空
- baostock 对于某些新股或停牌股可能没有数据
- 建议添加异常处理和日志记录

### 4. 日期格式问题
- 确保日期格式为 "YYYYMMDD"（如 "20240101"）
- baostock 需要的是 "YYYY-MM-DD" 格式，函数已自动转换

## 总结

✅ **已完成：** 全部 10 个文件的替换工作
- 1 个核心函数文件（stocks_Info.py）
- 9 个使用 ak.stock_zh_a_hist 的文件

✅ **已修复：** 循环导入问题
- 在 `common/stockBasic.py` 中使用延迟导入
- 修复 `ai_analysis_run.py` 的硬编码路径问题
- 所有测试通过 ✓

✅ **测试结果：**
- [OK] 所有模块导入正常
- [OK] baostock 数据获取正常
- [OK] 成功获取股票历史数据（测试：000001）

✅ **优势：**
- 免费、稳定、无需注册
- 数据源可靠（baostock 由证券从业者维护）
- 接口兼容，无需大幅修改代码逻辑

✅ **注意事项：**
- baostock 数据更新可能有 1-2 天延迟
- 不支持实时行情，仅历史数据
- 建议保留 akshare 用于其他功能（如实时行情、资金流向等）

## 相关文档

- `循环导入问题修复说明.md` - 详细的循环导入问题分析和解决方案
- `test_import_fix.py` - 自动化测试脚本，验证所有修复
