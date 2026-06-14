from __future__ import annotations

import json
import re
import math
from typing import Dict, List, Any, Optional
import configs as config
from common.logger import logger as project_logger
from auth import get_runtime_llm_config


class DeepSeekClient:
    """DeepSeek API客户端"""
    
    def __init__(self, model="deepseek-chat"):
        self.model = model
        self.logger = project_logger
        self.client = None

    def _get_client(self):
        """延迟初始化 OpenAI 客户端，避免页面加载时因 SSL/证书问题直接崩溃。"""
        if self.client is None:
            try:
                import openai
            except ModuleNotFoundError as exc:
                raise RuntimeError(
                    "AI依赖缺失：未安装 openai 包，请在当前虚拟环境执行 `python -m pip install openai httpx certifi` 后重试。"
                ) from exc

            llm_config = get_runtime_llm_config()
            if not llm_config["api_key"]:
                raise RuntimeError("当前用户未配置大模型 API Key，请先到“环境配置”页面保存当前账号的大模型配置。")

            self.client = openai.OpenAI(
                api_key=llm_config["api_key"],
                base_url=llm_config["base_url"]
            )
            if llm_config["model"]:
                self.model = llm_config["model"]
        return self.client

    @staticmethod
    def format_api_error(error: Exception | str) -> str:
        """Normalize provider errors to user-facing messages."""
        message = str(error)
        if "Insufficient Balance" in message or "Error code: 402" in message:
            return "AI服务暂不可用：API 账户余额不足（402 Insufficient Balance），请充值后重试。"
        return f"API调用失败: {message}"

    @staticmethod
    def is_api_error_message(message: Any) -> bool:
        """Check whether the returned text is an API failure message."""
        if not isinstance(message, str):
            return False
        return message.startswith("API调用失败:") or message.startswith("AI服务暂不可用：")

    @staticmethod
    def is_balance_error_message(message: Any) -> bool:
        """Check whether the returned text indicates insufficient balance."""
        if not isinstance(message, str):
            return False
        return "余额不足" in message or "Insufficient Balance" in message or "Error code: 402" in message

    @staticmethod
    def normalize_text(text: Any) -> str:
        """Normalize whitespace to avoid wasting tokens on formatting noise."""
        if text is None:
            return ""
        normalized = str(text).replace("\r\n", "\n").replace("\r", "\n")
        normalized = re.sub(r"[ \t]+", " ", normalized)
        normalized = re.sub(r"\n{3,}", "\n\n", normalized)
        return normalized.strip()

    @classmethod
    def truncate_text(cls, text: Any, max_chars: int = 2000, suffix: str = "\n...(已截断)") -> str:
        """Trim oversized text while keeping the prompt readable."""
        normalized = cls.normalize_text(text)
        if len(normalized) <= max_chars:
            return normalized
        if max_chars <= len(suffix):
            return normalized[:max_chars]
        return normalized[: max_chars - len(suffix)].rstrip() + suffix

    @classmethod
    def shrink_multiline_text(cls, text: Any, max_chars: int = 3200, max_lines: int = 40) -> str:
        """Keep the leading high-signal lines from large datasets."""
        normalized = cls.normalize_text(text)
        if not normalized:
            return ""

        lines = [line.strip() for line in normalized.splitlines() if line.strip()]
        if len(lines) > max_lines:
            lines = lines[:max_lines] + ["...(其余记录省略)"]
        return cls.truncate_text("\n".join(lines), max_chars=max_chars)

    @classmethod
    def build_context_digest(cls, text: Any, max_chars: int = 1200, max_lines: int = 14) -> str:
        """Build a short digest for downstream prompts to avoid re-feeding full reports."""
        normalized = cls.normalize_text(text)
        if not normalized:
            return ""

        raw_lines = [line.strip() for line in normalized.splitlines() if line.strip()]
        prioritized: List[str] = []
        regular: List[str] = []

        for line in raw_lines:
            if re.match(r"^(【[^】]+】|#+\s|[-*•]\s|\d+[\.、\)]\s|[A-Za-z][A-Za-z _-]{1,30}:)", line):
                prioritized.append(line)
            else:
                regular.append(line)

        selected: List[str] = []
        seen = set()
        for bucket in (prioritized, regular):
            for line in bucket:
                compact_line = re.sub(r"\s+", " ", line)
                if len(compact_line) > 180:
                    compact_line = compact_line[:177].rstrip() + "..."
                if compact_line in seen:
                    continue
                selected.append(compact_line)
                seen.add(compact_line)
                if len(selected) >= max_lines:
                    break
            if len(selected) >= max_lines:
                break

        digest_lines = []
        for line in selected:
            if re.match(r"^(【[^】]+】|#+\s|[-*•]\s|\d+[\.、\)])", line):
                digest_lines.append(line)
            else:
                digest_lines.append(f"- {line}")
        return cls.truncate_text("\n".join(digest_lines), max_chars=max_chars)

    @staticmethod
    def concise_output_instruction(word_limit: int = 700) -> str:
        """Common instruction used to keep responses concise."""
        return (
            f"\n输出要求：\n"
            f"1. 只保留对投资决策最重要的结论、证据、风险和建议。\n"
            f"2. 使用简洁 Markdown 或短段落，避免重复表述。\n"
            f"3. 若数据不足直接说明，不要展开泛泛背景。\n"
            f"4. 总字数尽量控制在 {word_limit} 字以内。\n"
        )

    @staticmethod
    def estimate_tokens(text: Any) -> int:
        """Rough token estimator for mixed Chinese/English text."""
        normalized = DeepSeekClient.normalize_text(text)
        if not normalized:
            return 0
        cjk_chars = len(re.findall(r"[\u4e00-\u9fff]", normalized))
        other_chars = max(len(normalized) - cjk_chars, 0)
        return cjk_chars + math.ceil(other_chars / 4)

    @classmethod
    def summarize_messages(cls, messages: List[Dict[str, str]]) -> Dict[str, int]:
        """Summarize prompt size for logging."""
        prompt_text = "\n".join(cls.normalize_text(message.get("content", "")) for message in messages)
        return {
            "message_count": len(messages),
            "chars": len(prompt_text),
            "estimated_tokens": cls.estimate_tokens(prompt_text)
        }

    @staticmethod
    def extract_usage(response: Any) -> Dict[str, int]:
        """Extract provider usage when available."""
        usage = getattr(response, "usage", None)
        if usage is None:
            return {}

        result = {}
        for key in (
            "prompt_tokens",
            "completion_tokens",
            "total_tokens",
            "prompt_cache_hit_tokens",
            "prompt_cache_miss_tokens"
        ):
            value = getattr(usage, key, None)
            if value is not None:
                result[key] = value
        return result
        
    def call_api(self, messages: List[Dict[str, str]], model: Optional[str] = None, 
                 temperature: float = 0.7, max_tokens: int = 2000,
                 include_reasoning: bool = False) -> str:
        """调用DeepSeek API"""
        # 使用实例的模型，如果没有传入则使用默认模型
        model_to_use = model or self.model
        
        # 对于 reasoner 模型，仅在需要展示推理链时放宽输出长度
        if "reasoner" in model_to_use.lower():
            max_tokens = max(max_tokens, 3000 if not include_reasoning else 5000)

        normalized_messages = [
            {
                "role": message.get("role", "user"),
                "content": self.normalize_text(message.get("content", ""))
            }
            for message in messages
        ]
        original_stats = self.summarize_messages(messages)
        normalized_stats = self.summarize_messages(normalized_messages)
        
        try:
            client = self._get_client()
            response = client.chat.completions.create(
                model=model_to_use,
                messages=normalized_messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            # 处理 reasoner 模型的响应
            message = response.choices[0].message
            
            result = ""
            
            if include_reasoning and hasattr(message, 'reasoning_content') and message.reasoning_content:
                result += f"【推理过程】\n{message.reasoning_content}\n\n"
            
            if message.content:
                result += self.normalize_text(message.content)

            output_stats = {
                "chars": len(result),
                "estimated_tokens": self.estimate_tokens(result)
            }
            usage_stats = self.extract_usage(response)
            self.logger.info(
                "[LLM] model=%s msgs=%s prompt_chars=%s normalized_prompt_chars=%s "
                "prompt_est_tokens=%s normalized_prompt_est_tokens=%s "
                "completion_chars=%s completion_est_tokens=%s max_tokens=%s usage=%s",
                model_to_use,
                original_stats["message_count"],
                original_stats["chars"],
                normalized_stats["chars"],
                original_stats["estimated_tokens"],
                normalized_stats["estimated_tokens"],
                output_stats["chars"],
                output_stats["estimated_tokens"],
                max_tokens,
                usage_stats or "n/a"
            )
            
            return result if result else "API返回空响应"
            
        except Exception as e:
            return self.format_api_error(e)
    
    def technical_analysis(self, stock_info: Dict, stock_data: Any, indicators: Dict) -> str:
        """技术面分析"""
        prompt = f"""
你是一名资深的技术分析师。请基于以下股票数据进行专业的技术面分析：

股票信息：
- 股票代码：{stock_info.get('symbol', 'N/A')}
- 股票名称：{stock_info.get('name', 'N/A')}
- 当前价格：{stock_info.get('current_price', 'N/A')}
- 涨跌幅：{stock_info.get('change_percent', 'N/A')}%

最新技术指标：
- 收盘价：{indicators.get('price', 'N/A')}
- MA5：{indicators.get('ma5', 'N/A')}
- MA10：{indicators.get('ma10', 'N/A')}
- MA20：{indicators.get('ma20', 'N/A')}
- MA60：{indicators.get('ma60', 'N/A')}
- RSI：{indicators.get('rsi', 'N/A')}
- MACD：{indicators.get('macd', 'N/A')}
- MACD信号线：{indicators.get('macd_signal', 'N/A')}
- 布林带上轨：{indicators.get('bb_upper', 'N/A')}
- 布林带下轨：{indicators.get('bb_lower', 'N/A')}
- K值：{indicators.get('k_value', 'N/A')}
- D值：{indicators.get('d_value', 'N/A')}
- 量比：{indicators.get('volume_ratio', 'N/A')}

请从以下角度进行分析：
1. 趋势分析（均线系统、价格走势）
2. 超买超卖分析（RSI、KDJ）
3. 动量分析（MACD）
4. 支撑阻力分析（布林带）
5. 成交量分析
6. 短期、中期、长期技术判断
7. 关键技术位分析

请给出专业、详细的技术分析报告，包含风险提示。
{self.concise_output_instruction(500)}
"""
        
        messages = [
            {"role": "system", "content": "你是一名经验丰富的股票技术分析师，具有深厚的技术分析功底。"},
            {"role": "user", "content": prompt}
        ]
        
        return self.call_api(messages, max_tokens=1200)
    
    def fundamental_analysis(self, stock_info: Dict, financial_data: Dict = None, quarterly_data: Dict = None) -> str:
        """基本面分析"""
        
        # 构建财务数据部分
        financial_section = ""
        if financial_data and not financial_data.get('error'):
            ratios = financial_data.get('financial_ratios', {})
            if ratios:
                financial_section = f"""
详细财务指标：
【盈利能力】
- 净资产收益率(ROE)：{ratios.get('净资产收益率ROE', ratios.get('ROE', 'N/A'))}
- 总资产收益率(ROA)：{ratios.get('总资产收益率ROA', ratios.get('ROA', 'N/A'))}
- 销售毛利率：{ratios.get('销售毛利率', ratios.get('毛利率', 'N/A'))}
- 销售净利率：{ratios.get('销售净利率', ratios.get('净利率', 'N/A'))}

【偿债能力】
- 资产负债率：{ratios.get('资产负债率', 'N/A')}
- 流动比率：{ratios.get('流动比率', 'N/A')}
- 速动比率：{ratios.get('速动比率', 'N/A')}

【运营能力】
- 存货周转率：{ratios.get('存货周转率', 'N/A')}
- 应收账款周转率：{ratios.get('应收账款周转率', 'N/A')}
- 总资产周转率：{ratios.get('总资产周转率', 'N/A')}

【成长能力】
- 营业收入同比增长：{ratios.get('营业收入同比增长', ratios.get('收入增长', 'N/A'))}
- 净利润同比增长：{ratios.get('净利润同比增长', ratios.get('盈利增长', 'N/A'))}

【每股指标】
- 每股收益(EPS)：{ratios.get('EPS', 'N/A')}
- 每股账面价值：{ratios.get('每股账面价值', 'N/A')}
- 股息率：{ratios.get('股息率', stock_info.get('dividend_yield', 'N/A'))}
- 派息率：{ratios.get('派息率', 'N/A')}
"""
            
            # 添加报告期信息
            if ratios.get('报告期'):
                financial_section = f"\n财务数据报告期：{ratios.get('报告期')}\n" + financial_section
        
        # 构建季报数据部分
        quarterly_section = ""
        if quarterly_data and quarterly_data.get('data_success'):
            # 使用格式化的季报数据
            from quarterly_report_data import QuarterlyReportDataFetcher
            fetcher = QuarterlyReportDataFetcher()
            quarterly_section = f"""

【最近8期季报详细数据】
{self.shrink_multiline_text(fetcher.format_quarterly_reports_for_ai(quarterly_data), max_chars=2800, max_lines=36)}

以上是通过akshare获取的最近8期季度财务报告，请重点基于这些数据进行趋势分析。
"""
        
        prompt = f"""
你是一名资深的基本面分析师，拥有CFA资格和10年以上的证券分析经验。请基于以下详细信息进行深入的基本面分析：

【基本信息】
- 股票代码：{stock_info.get('symbol', 'N/A')}
- 股票名称：{stock_info.get('name', 'N/A')}
- 当前价格：{stock_info.get('current_price', 'N/A')}
- 市值：{stock_info.get('market_cap', 'N/A')}
- 行业：{stock_info.get('sector', 'N/A')}
- 细分行业：{stock_info.get('industry', 'N/A')}

【估值指标】
- 市盈率(PE)：{stock_info.get('pe_ratio', 'N/A')}
- 市净率(PB)：{stock_info.get('pb_ratio', 'N/A')}
- 市销率(PS)：{stock_info.get('ps_ratio', 'N/A')}
- Beta系数：{stock_info.get('beta', 'N/A')}
- 52周最高：{stock_info.get('52_week_high', 'N/A')}
- 52周最低：{stock_info.get('52_week_low', 'N/A')}
{financial_section}
{quarterly_section}

请从以下维度进行专业、深入的分析：

1. **公司质地分析**
   - 业务模式和核心竞争力
   - 行业地位和市场份额
   - 护城河分析（品牌、技术、规模等）

2. **盈利能力分析**
   - ROE和ROA水平评估
   - 毛利率和净利率趋势
   - 与行业平均水平对比
   - 盈利质量和持续性

3. **财务健康度分析**
   - 资产负债结构
   - 偿债能力评估
   - 现金流状况
   - 财务风险识别

4. **成长性分析**
   - 收入和利润增长趋势
   - 增长驱动因素
   - 未来成长空间
   - 行业发展前景

5. **季报趋势分析（如有季报数据）** ⭐ 重点分析
   - **营收趋势**：分析最近8期营业收入的变化趋势，识别增长或下滑
   - **利润趋势**：分析净利润和每股收益的变化，评估盈利能力变化
   - **现金流分析**：经营现金流、投资现金流、筹资现金流的变化趋势
   - **资产负债变化**：资产规模、负债水平、所有者权益的变化
   - **季度环比/同比**：计算关键指标的环比和同比变化率
   - **经营质量**：评估收入质量、利润质量、现金流质量
   - **异常识别**：识别异常波动，分析原因（季节性、一次性事件等）
   - **趋势预判**：基于最近8期数据预判未来1-2个季度趋势

6. **估值分析**
   - 当前估值水平（PE、PB）
   - 历史估值区间对比
   - 行业估值对比
   - 结合季报趋势调整估值预期
   - 合理估值区间判断

7. **投资价值判断**
   - 综合评分（0-100分）
   - 投资亮点（特别关注季报改善趋势）
   - 投资风险（关注季报恶化信号）
   - 适合的投资者类型

**分析要求：**
- 如果有季报数据，请重点分析8期数据的趋势变化
- 识别改善或恶化的早期信号
- 结合季报数据对未来业绩进行预判
- 数据分析要深入，结论要有依据
- 结合当前市场环境和行业发展趋势

请给出专业、详细的基本面分析报告。
{self.concise_output_instruction(700)}
"""
        
        messages = [
            {"role": "system", "content": "你是一名经验丰富的股票基本面分析师，擅长公司财务分析和行业研究。"},
            {"role": "user", "content": prompt}
        ]
        
        return self.call_api(messages, max_tokens=1600)
    
    def fund_flow_analysis(self, stock_info: Dict, indicators: Dict, fund_flow_data: Dict = None) -> str:
        """资金面分析"""
        
        # 构建资金流向数据部分 - 使用akshare格式化数据
        fund_flow_section = ""
        if fund_flow_data and fund_flow_data.get('data_success'):
            # 使用格式化的资金流向数据
            from fund_flow_akshare import FundFlowAkshareDataFetcher
            fetcher = FundFlowAkshareDataFetcher()
            fund_flow_section = f"""

【近20个交易日资金流向详细数据】
{self.shrink_multiline_text(fetcher.format_fund_flow_for_ai(fund_flow_data), max_chars=2600, max_lines=34)}

以上是通过akshare从东方财富获取的实际资金流向数据，请重点基于这些数据进行趋势分析。
"""
        else:
            fund_flow_section = "\n【资金流向数据】\n注意：未能获取到资金流向数据，将基于成交量进行分析。\n"
        
        prompt = f"""
你是一名资深的资金面分析师，擅长从资金流向数据中洞察主力行为和市场趋势。

【基本信息】
股票代码：{stock_info.get('symbol', 'N/A')}
股票名称：{stock_info.get('name', 'N/A')}
当前价格：{stock_info.get('current_price', 'N/A')}
市值：{stock_info.get('market_cap', 'N/A')}

【技术指标】
- 量比：{indicators.get('volume_ratio', 'N/A')}
- 当前成交量与5日均量比：{indicators.get('volume_ratio', 'N/A')}
{fund_flow_section}

【分析要求】

请你**基于上述近20个交易日的完整资金流向数据**，从以下角度进行深入分析：

1. **资金流向趋势分析** ⭐ 重点
   - 分析近20个交易日主力资金的累计净流入/净流出
   - 识别资金流向的趋势性特征（持续流入、持续流出、震荡）
   - 计算主力资金净流入天数占比
   - 评估资金流向强度（累计金额、平均每日金额）

2. **主力资金行为分析** ⭐ 核心重点
   - **主力资金总体表现**：累计净流入金额、占比、趋势方向
   - **超大单分析**：机构大资金的进出动作
   - **大单分析**：主力资金的操作特征
   - **主力操作意图研判**：
     * 吸筹建仓：持续净流入 + 股价上涨/盘整
     * 派发出货：持续净流出 + 股价下跌/高位
     * 洗盘整理：震荡流入流出 + 股价调整
     * 拉升推动：集中大额流入 + 股价快速上涨

3. **散户资金行为分析**
   - **中单、小单的动向**：散户的买卖情绪
   - **主力与散户博弈**：
     * 主力流入、散户流出 → 专业资金吸筹
     * 主力流出、散户流入 → 高位接盘风险
     * 同向流动 → 趋势明确
   - 散户参与度和情绪判断

4. **量价配合分析**
   - 资金流向与股价涨跌的配合度
   - 识别量价背离：
     * 价涨量缩 + 资金流出 → 警惕顶部
     * 价跌量增 + 资金流入 → 可能见底
   - 成交活跃度变化趋势

5. **关键信号识别**
   - **买入信号**：
     * 主力持续净流入
     * 大单明显流入
     * 资金流入 + 股价上涨
   - **卖出信号**：
     * 主力持续净流出
     * 大额资金出逃
     * 资金流出 + 股价滞涨或下跌
   - **观望信号**：
     * 资金流向不明确
     * 主力与散户博弈激烈

6. **阶段性特征**
   - 早期阶段（前10个交易日）vs 近期阶段（后10个交易日）
   - 资金流向的变化趋势
   - 转折点识别

7. **投资建议**
   - 基于资金流向的操作建议
   - 关注重点和风险提示
   - 资金面对后市的指示意义
   - 未来资金流向预判

8. **投资建议**
   - 基于资金面的明确操作建议
   - 买入/持有/卖出的判断依据
   - 仓位管理建议

【分析原则】
- 主力资金持续流入 + 股价上涨 → 强势信号，主力看好
- 主力资金流出 + 股价上涨 → 警惕信号，可能是散户接盘
- 主力资金流入 + 股价下跌 → 可能是主力低位吸筹
- 主力资金流出 + 股价下跌 → 弱势信号，主力看空
- 注意区分短期波动与趋势性变化

请给出专业、详细、有深度的资金面分析报告。记住：要基于问财数据的实际内容进行分析，而不是假设！
{self.concise_output_instruction(600)}
"""
        
        messages = [
            {"role": "system", "content": "你是一名经验丰富的资金面分析师，擅长市场资金流向和主力行为分析，能够深入解读资金数据背后的投资逻辑。"},
            {"role": "user", "content": prompt}
        ]
        
        return self.call_api(messages, max_tokens=1400)
    
    def comprehensive_discussion(self, technical_report: str, fundamental_report: str, 
                               fund_flow_report: str, stock_info: Dict) -> str:
        """综合讨论"""
        technical_digest = self.build_context_digest(technical_report, max_chars=900)
        fundamental_digest = self.build_context_digest(fundamental_report, max_chars=900)
        fund_flow_digest = self.build_context_digest(fund_flow_report, max_chars=900)

        prompt = f"""
现在需要进行一场投资决策会议，你作为首席分析师，需要综合各位分析师的报告进行讨论。

股票基本信息：
- 股票代码：{stock_info.get('symbol', 'N/A')}
- 股票名称：{stock_info.get('name', 'N/A')}
- 当前价格：{stock_info.get('current_price', 'N/A')}

技术面分析报告：
{technical_digest}

基本面分析报告：
{fundamental_digest}

资金面分析报告：
{fund_flow_digest}

请作为首席分析师，综合以上三个维度的分析报告，进行深入讨论：

1. 各个分析维度的一致性和分歧点
2. 不同分析结论的权重考量
3. 当前市场环境下的投资逻辑
4. 潜在风险和机会识别
5. 不同投资周期的考量（短期、中期、长期）
6. 市场情绪和预期管理

请输出一份简明会议纪要，重点写结论、分歧、风险收益比和执行建议，不要展开冗长对话。
{self.concise_output_instruction(550)}
"""
        
        messages = [
            {"role": "system", "content": "你是一名资深的首席投资分析师，擅长综合不同维度的分析形成投资判断。"},
            {"role": "user", "content": prompt}
        ]
        
        return self.call_api(messages, max_tokens=1200)
    
    def final_decision(self, comprehensive_discussion: str, stock_info: Dict, 
                      indicators: Dict) -> Dict[str, Any]:
        """最终投资决策"""
        discussion_digest = self.build_context_digest(comprehensive_discussion, max_chars=1200)

        prompt = f"""
基于前期的综合分析讨论，现在需要做出最终的投资决策。

股票信息：
- 股票代码：{stock_info.get('symbol', 'N/A')}
- 股票名称：{stock_info.get('name', 'N/A')}
- 当前价格：{stock_info.get('current_price', 'N/A')}

综合分析讨论结果：
{discussion_digest}

当前关键技术位：
- MA20：{indicators.get('ma20', 'N/A')}
- 布林带上轨：{indicators.get('bb_upper', 'N/A')}
- 布林带下轨：{indicators.get('bb_lower', 'N/A')}

请给出最终投资决策，必须包含以下内容：

1. 投资评级：买入/持有/卖出
2. 目标价位（具体数字）
3. 操作建议（具体的买入/卖出策略）
4. 进场位置（具体价位区间）
5. 止盈位置（具体价位）
6. 止损位置（具体价位）
7. 持有周期建议
8. 风险提示
9. 仓位建议（轻仓/中等仓位/重仓）

请严格以 JSON 格式输出，不要附加说明文字，格式如下：
{{
    "rating": "买入/持有/卖出",
    "target_price": "目标价位数字",
    "operation_advice": "具体操作建议",
    "entry_range": "进场价位区间",
    "take_profit": "止盈价位",
    "stop_loss": "止损价位",
    "holding_period": "持有周期",
    "position_size": "仓位建议",
    "risk_warning": "风险提示",
    "confidence_level": "信心度(1-10分)"
}}
"""
        
        messages = [
            {"role": "system", "content": "你是一名专业的投资决策专家，需要给出明确、可执行的投资建议。"},
            {"role": "user", "content": prompt}
        ]
        
        response = self.call_api(messages, temperature=0.3, max_tokens=900)
        
        try:
            # 尝试解析JSON响应
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                decision_json = json.loads(json_match.group())
                return decision_json
            else:
                # 如果无法解析JSON，返回文本响应
                return {"decision_text": response}
        except:
            return {"decision_text": response}
