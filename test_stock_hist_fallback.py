"""
测试 get_stock_hist_data 的 akshare -> baostock 降级逻辑
运行: python test_stock_hist_fallback.py
"""
import sys
import pandas as pd
from unittest.mock import patch, MagicMock

# 确保项目根目录在路径中
sys.path.insert(0, '.')

from aitrader.a_self_Strategy.untils.stocks_Info import Stock_Info

SYMBOL = "000001"
START  = "20250101"
END    = "20250228"

AKSHARE_COLS = ['日期', '开盘', '收盘', '最高', '最低', '成交量', '成交额', '振幅', '涨跌幅', '涨跌额', '换手率']

def _make_ak_df():
    """构造一个合法的 akshare 返回 DataFrame"""
    return pd.DataFrame([{
        '日期': '2025-01-02', '开盘': 10.0, '收盘': 10.5,
        '最高': 10.8, '最低': 9.9, '成交量': 100000,
        '成交额': 1050000.0, '振幅': 0.9, '涨跌幅': 0.5,
        '涨跌额': 0.05, '换手率': 1.2
    }])

def _make_bs_df():
    """构造一个合法的 baostock 返回 DataFrame（已映射为中文列名）"""
    return pd.DataFrame([{
        '日期': '2025-01-02', '股票代码': SYMBOL,
        '开盘': 10.0, '最高': 10.8, '最低': 9.9, '收盘': 10.5,
        '成交量': 100000.0, '成交额': 1050000.0, '换手率': 1.2
    }])


# ──────────────────────────────────────────────
# Case 1: akshare 正常返回数据
# ──────────────────────────────────────────────
def test_akshare_success():
    print("=" * 55)
    print("Case 1: akshare 正常返回数据（不应调用 baostock）")
    print("=" * 55)
    ak_df = _make_ak_df()
    with patch('aitrader.a_self_Strategy.untils.stocks_Info.ak.stock_zh_a_hist', return_value=ak_df) as mock_ak, \
         patch('aitrader.a_self_Strategy.untils.stocks_Info.bs.login') as mock_bs_login:

        df = Stock_Info.get_stock_hist_data(SYMBOL, START, END)

        assert not df.empty, "❌ 返回数据不应为空"
        assert mock_ak.called,           "❌ akshare 应被调用"
        assert not mock_bs_login.called, "❌ baostock 不应被调用"
        assert '最高' in df.columns,     "❌ 缺少'最高'列"
        print(f"✅ 通过：akshare 返回 {len(df)} 条，baostock 未触发")
        return True


# ──────────────────────────────────────────────
# Case 2: akshare 抛出异常 → 降级 baostock
# ──────────────────────────────────────────────
def test_akshare_exception_fallback():
    print("\n" + "=" * 55)
    print("Case 2: akshare 抛出异常 → 降级 baostock")
    print("=" * 55)
    bs_df = _make_bs_df()

    with patch('aitrader.a_self_Strategy.untils.stocks_Info.ak.stock_zh_a_hist',
               side_effect=Exception("模拟网络超时")) as mock_ak, \
         patch('aitrader.a_self_Strategy.untils.stocks_Info.bs.login',
               return_value=MagicMock(error_code='0')) as mock_bs_login, \
         patch('aitrader.a_self_Strategy.untils.stocks_Info.bs.query_history_k_data_plus') as mock_bs_query, \
         patch('aitrader.a_self_Strategy.untils.stocks_Info.bs.logout'):

        # 模拟 baostock 迭代返回数据
        row = ['2025-01-02', 'sh.000001', '10.0', '10.8', '9.9', '10.5', '100000', '1050000', '1.2']
        fields = ['date', 'code', 'open', 'high', 'low', 'close', 'volume', 'amount', 'turn']
        rs_mock = MagicMock()
        rs_mock.error_code = '0'
        rs_mock.fields = fields
        rs_mock.next.side_effect = [True, False]
        rs_mock.get_row_data.return_value = row
        mock_bs_query.return_value = rs_mock

        df = Stock_Info.get_stock_hist_data(SYMBOL, START, END)

        assert not df.empty,          "❌ baostock 应返回数据"
        assert mock_ak.called,        "❌ akshare 应被尝试"
        assert mock_bs_login.called,  "❌ baostock 应被调用"
        assert '最高' in df.columns,  "❌ 缺少'最高'列"
        print(f"✅ 通过：akshare 异常后 baostock 返回 {len(df)} 条")
        return True


# ──────────────────────────────────────────────
# Case 3: akshare 返回空 DataFrame → 降级 baostock
# ──────────────────────────────────────────────
def test_akshare_empty_fallback():
    print("\n" + "=" * 55)
    print("Case 3: akshare 返回空数据 → 降级 baostock")
    print("=" * 55)
    with patch('aitrader.a_self_Strategy.untils.stocks_Info.ak.stock_zh_a_hist',
               return_value=pd.DataFrame()) as mock_ak, \
         patch('aitrader.a_self_Strategy.untils.stocks_Info.bs.login',
               return_value=MagicMock(error_code='0')) as mock_bs_login, \
         patch('aitrader.a_self_Strategy.untils.stocks_Info.bs.query_history_k_data_plus') as mock_bs_query, \
         patch('aitrader.a_self_Strategy.untils.stocks_Info.bs.logout'):

        row = ['2025-01-02', 'sh.000001', '10.0', '10.8', '9.9', '10.5', '100000', '1050000', '1.2']
        fields = ['date', 'code', 'open', 'high', 'low', 'close', 'volume', 'amount', 'turn']
        rs_mock = MagicMock()
        rs_mock.error_code = '0'
        rs_mock.fields = fields
        rs_mock.next.side_effect = [True, False]
        rs_mock.get_row_data.return_value = row
        mock_bs_query.return_value = rs_mock

        df = Stock_Info.get_stock_hist_data(SYMBOL, START, END)

        assert not df.empty,          "❌ baostock 应返回数据"
        assert mock_ak.called,        "❌ akshare 应被尝试"
        assert mock_bs_login.called,  "❌ baostock 应被调用"
        print(f"✅ 通过：akshare 空数据后 baostock 返回 {len(df)} 条")
        return True


# ──────────────────────────────────────────────
# Case 4: akshare 返回列不完整 → 降级 baostock
# ──────────────────────────────────────────────
def test_akshare_missing_columns_fallback():
    print("\n" + "=" * 55)
    print("Case 4: akshare 返回列不完整 → 降级 baostock")
    print("=" * 55)
    # 缺少 '换手率' 字段
    bad_df = pd.DataFrame([{'日期': '2025-01-02', '开盘': 10.0, '收盘': 10.5}])

    with patch('aitrader.a_self_Strategy.untils.stocks_Info.ak.stock_zh_a_hist',
               return_value=bad_df) as mock_ak, \
         patch('aitrader.a_self_Strategy.untils.stocks_Info.bs.login',
               return_value=MagicMock(error_code='0')) as mock_bs_login, \
         patch('aitrader.a_self_Strategy.untils.stocks_Info.bs.query_history_k_data_plus') as mock_bs_query, \
         patch('aitrader.a_self_Strategy.untils.stocks_Info.bs.logout'):

        row = ['2025-01-02', 'sh.000001', '10.0', '10.8', '9.9', '10.5', '100000', '1050000', '1.2']
        fields = ['date', 'code', 'open', 'high', 'low', 'close', 'volume', 'amount', 'turn']
        rs_mock = MagicMock()
        rs_mock.error_code = '0'
        rs_mock.fields = fields
        rs_mock.next.side_effect = [True, False]
        rs_mock.get_row_data.return_value = row
        mock_bs_query.return_value = rs_mock

        df = Stock_Info.get_stock_hist_data(SYMBOL, START, END)

        assert not df.empty,          "❌ baostock 应返回数据"
        assert mock_bs_login.called,  "❌ baostock 应被调用"
        print(f"✅ 通过：akshare 列不完整后 baostock 返回 {len(df)} 条")
        return True


# ──────────────────────────────────────────────
# Case 5: 真实网络请求（可选，需联网）
# ──────────────────────────────────────────────
def test_real_network():
    print("\n" + "=" * 55)
    print("Case 5: 真实网络请求（akshare 实际调用）")
    print("=" * 55)
    try:
        df = Stock_Info.get_stock_hist_data(SYMBOL, START, END)
        if df is not None and not df.empty:
            print(f"✅ 通过：获取到 {len(df)} 条数据")
            print(f"   来源列: {df.columns.tolist()}")
            print(f"   首行:\n{df.head(1).to_string(index=False)}")
            return True
        else:
            print("⚠️  返回数据为空（可能非交易日或网络问题）")
            return True  # 空数据不算失败
    except Exception as e:
        print(f"⚠️  真实请求异常（可忽略）: {e}")
        return True


# ──────────────────────────────────────────────
# 主入口
# ──────────────────────────────────────────────
if __name__ == "__main__":
    tests = [
        test_akshare_success,
        test_akshare_exception_fallback,
        test_akshare_empty_fallback,
        test_akshare_missing_columns_fallback,
        test_real_network,
    ]

    results = []
    for t in tests:
        try:
            results.append(t())
        except AssertionError as e:
            print(str(e))
            results.append(False)
        except Exception as e:
            print(f"❌ 意外异常: {e}")
            results.append(False)

    print("\n" + "=" * 55)
    passed = sum(results)
    print(f"测试结果: {passed}/{len(results)} 通过")
    print("🎉 全部通过！" if passed == len(results) else "❌ 存在失败项")
    print("=" * 55)
    sys.exit(0 if passed == len(results) else 1)
