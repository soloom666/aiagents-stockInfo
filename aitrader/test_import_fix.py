# -*- coding: utf-8 -*-
"""
测试循环导入修复、baostock 替代方案和代理配置
"""
import sys
import os

# 添加项目根目录到 Python 路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# 初始化代理配置
from common.proxy_config import ProxyConfig
ProxyConfig.init_akshare_proxy()

def test_imports():
    """测试所有关键模块的导入"""
    print("=" * 60)
    print("测试模块导入")
    print("=" * 60)

    try:
        print("\n1. 测试 Stock_Info 导入...")
        from a_self_Strategy.untils.stocks_Info import Stock_Info
        print("   [OK] Stock_Info 导入成功")
    except Exception as e:
        print(f"   [FAIL] Stock_Info 导入失败: {e}")
        return False

    try:
        print("\n2. 测试 stockBasic 导入...")
        from common.stockBasic import stock_to_csv
        print("   [OK] stockBasic 导入成功")
    except Exception as e:
        print(f"   [FAIL] stockBasic 导入失败: {e}")
        return False

    try:
        print("\n3. 测试 al_yaogu 导入...")
        from a_self_Strategy.strategy.al_yaogu import yaogu_qibao_test
        print("   [OK] al_yaogu 导入成功")
    except Exception as e:
        print(f"   [FAIL] al_yaogu 导入失败: {e}")
        return False

    try:
        print("\n4. 测试 macd_boll 导入...")
        from a_self_Strategy.strategy.macd_boll import macd_boll
        print("   [OK] macd_boll 导入成功")
    except Exception as e:
        print(f"   [FAIL] macd_boll 导入失败: {e}")
        return False

    try:
        print("\n5. 测试 ai_analysis_run 导入...")
        from a_self_Strategy.ai_analysis.ai_analysis_run import AiAnalysis
        print("   [OK] ai_analysis_run 导入成功")
    except Exception as e:
        print(f"   [FAIL] ai_analysis_run 导入失败: {e}")
        return False

    return True


def test_get_stock_hist_data():
    """测试 get_stock_hist_data 函数"""
    print("\n" + "=" * 60)
    print("测试 get_stock_hist_data 函数")
    print("=" * 60)

    try:
        from a_self_Strategy.untils.stocks_Info import Stock_Info

        print("\n测试获取股票数据（000001，最近30天）...")
        from datetime import datetime, timedelta
        end_date = datetime.now().strftime("%Y%m%d")
        start_date = (datetime.now() - timedelta(days=30)).strftime("%Y%m%d")

        df = Stock_Info.get_stock_hist_data(
            symbol='000001',
            start_date=start_date,
            end_date=end_date,
            period="daily",
            adjust=""
        )

        if df is not None and not df.empty:
            print(f"   [OK] 成功获取数据，共 {len(df)} 条记录")
            print(f"   数据列: {df.columns.tolist()}")
            print(f"\n   前3条数据:")
            print(df.head(3).to_string())
            return True
        else:
            print("   [WARN] 获取的数据为空")
            return False

    except Exception as e:
        print(f"   [FAIL] 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    print("\n开始测试循环导入修复和 baostock 替代方案...")
    print()

    # 测试导入
    import_success = test_imports()

    # 测试数据获取
    if import_success:
        data_success = test_get_stock_hist_data()
    else:
        data_success = False

    # 总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    if import_success and data_success:
        print("[SUCCESS] 所有测试通过！")
        print("\n修复说明:")
        print("1. [OK] 循环导入问题已修复（使用延迟导入）")
        print("2. [OK] baostock 替代 akshare 正常工作")
        print("3. [OK] 所有模块导入正常")
    elif import_success:
        print("[PARTIAL] 导入测试通过，但数据获取测试失败")
        print("   请检查网络连接或 baostock 服务状态")
    else:
        print("[FAIL] 测试失败，请检查错误信息")

    print("=" * 60)
