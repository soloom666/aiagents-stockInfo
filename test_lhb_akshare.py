"""
测试 akshare 龙虎榜备用数据源
运行方式：python test_lhb_akshare.py
"""
import akshare as ak
import inspect
from datetime import datetime, timedelta

# -- 1. 列出当前 akshare 版本所有龙虎榜函数 --
print("=" * 60)
print("akshare 版本:", ak.__version__)
lhb_funcs = [f for f in dir(ak) if 'lhb' in f.lower()]
print("龙虎榜相关函数:", lhb_funcs)
print()

# -- 2. 查看 stock_lhb_detail_em 签名 --
func = getattr(ak, 'stock_lhb_detail_em', None)
if func:
    print("stock_lhb_detail_em 签名:", inspect.signature(func))
else:
    print("stock_lhb_detail_em 不存在")
print()

# -- 3. 实际调用测试（最近一个工作日）--
test_date = datetime.now()
if test_date.weekday() >= 5:          # 周末往前推到周五
    test_date -= timedelta(days=test_date.weekday() - 4)
date_str = test_date.strftime('%Y-%m-%d')
date_ak  = date_str.replace('-', '')
print(f"测试日期: {date_str} ({date_ak})")
print()

# 尝试新版参数
print("-- 尝试 start_date/end_date --")
try:
    df = ak.stock_lhb_detail_em(start_date=date_ak, end_date=date_ak)
    print(f"  成功，行数={len(df)}，列名={list(df.columns)}")
    if not df.empty:
        print(df.head(2).to_string())
except Exception as e:
    print(f"  失败: {e}")

print()

# 尝试旧版参数
print("-- 尝试 date= --")
try:
    df2 = ak.stock_lhb_detail_em(date=date_ak)
    print(f"  成功，行数={len(df2)}，列名={list(df2.columns)}")
    if not df2.empty:
        print(df2.head(2).to_string())
except Exception as e:
    print(f"  失败: {e}")

print()

# -- 4. 通过 LonghubangDataFetcher 测试完整降级流程 --
print("=" * 60)
print("测试完整降级流程 (_get_akshare_longhubang_data)")
from longhubang_data import LonghubangDataFetcher
fetcher = LonghubangDataFetcher()
result = fetcher._get_akshare_longhubang_data(date_str)
if result and result.get('data'):
    print(f"成功获取 {len(result['data'])} 条记录，首条: {result['data'][0]}")
else:
    print("未获取到数据")
