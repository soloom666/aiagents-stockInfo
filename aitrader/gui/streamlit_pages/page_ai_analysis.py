import streamlit as st
import pandas as pd
from common.logger import logger
import sys
import os

# 添加路径以便导入模块
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..', '..'))
sys.path.insert(0, project_root)

from a_self_Strategy.ai_analysis.ai_analysis_run import AiAnalysis


def build_page():
    st.title("🤖 AI股票分析 - 寻龙策略")

    st.markdown("""
    ### 策略说明
    - **MACD策略**: 基于MACD和布林带的技术指标分析
    - **妖股策略**: 基于妖股七豹策略的筛选
    - **AI Agent推荐**: AI智��分析推荐的股票
    """)

    # 创建按钮
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        long_button = st.button("🚀 运行寻龙策略", type="primary", use_container_width=True)

    # 当点击按钮时
    if long_button:
        with st.spinner('正在运行AI分析策略，请稍候...'):
            try:
                # 调用xunlong方法获取推荐股票
                recommend_stocks = AiAnalysis.xunlong()

                if recommend_stocks:
                    st.success("✅ 分析完成！")

                    # 创建三列布局展示不同策略的结果
                    col1, col2, col3 = st.columns(3)

                    # 显示MACD策略股票
                    with col1:
                        st.markdown("### 📊 MACD策略推荐")
                        macd_stocks = recommend_stocks.get('macd', [])
                        if macd_stocks:
                            st.metric("推荐股票数量", len(macd_stocks))
                            df_macd = pd.DataFrame({
                                '股票代码': macd_stocks
                            })
                            st.dataframe(df_macd, use_container_width=True)
                        else:
                            st.info("暂无推荐股票")

                    # 显示妖股策略股票
                    with col2:
                        st.markdown("### 🔥 妖股策略推荐")
                        yaogu_stocks = recommend_stocks.get('yaogu', [])
                        if yaogu_stocks:
                            st.metric("推荐股票数量", len(yaogu_stocks))
                            df_yaogu = pd.DataFrame({
                                '股票代码': yaogu_stocks
                            })
                            st.dataframe(df_yaogu, use_container_width=True)
                        else:
                            st.info("暂无推荐股票")

                    # 显示AI Agent推荐股票
                    with col3:
                        st.markdown("### 🤖 AI Agent推荐")
                        ai_agent_stocks = recommend_stocks.get('al_agent_stocks', [])
                        if ai_agent_stocks:
                            st.metric("推荐股票数量", len(ai_agent_stocks))
                            df_agent = pd.DataFrame({
                                '股票代码': ai_agent_stocks
                            })
                            st.dataframe(df_agent, use_container_width=True)
                        else:
                            st.info("暂无推荐股票")

                    # 显示差异信息（如果有）
                    if 'diff' in recommend_stocks and recommend_stocks['diff']:
                        st.markdown("---")
                        st.markdown("### 🆕 新增推荐股票")
                        diff_stocks = recommend_stocks['diff']
                        df_diff = pd.DataFrame({
                            '股票代码': diff_stocks
                        })
                        st.dataframe(df_diff, use_container_width=True)
                        st.warning(f"发现 {len(diff_stocks)} 只新增推荐股票，已发送邮件通知！")

                    # 显示完整数据（可折叠）
                    with st.expander("📋 查看完整推荐数据"):
                        st.json(recommend_stocks)

                else:
                    st.warning("未获取到推荐股票数据")

            except Exception as e:
                logger.error(f"运行寻龙策略失败: {e}")
                st.error(f"❌ 运行失败: {str(e)}")
                st.exception(e)

    # 添加使用说明
    with st.expander("ℹ️ 使用说明"):
        st.markdown("""
        1. 点击「运行寻龙策略」按钮开始分析
        2. 系统会自动运行三种策略：
           - MACD布林带策略
           - 妖股七豹策略
           - AI智能分析
        3. 分析结果会自动保存到JSON文件
        4. 如果发现新的推荐股票，系统会自动发送邮件通知
        5. 分析结果也会追加到Excel文件中
        """)
