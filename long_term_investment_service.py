"""
长线投资筛选服务
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import io
import math
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional

import akshare as ak
import pandas as pd

from common.logger import logger
from data_source_manager import data_source_manager
from quarterly_report_data import QuarterlyReportDataFetcher


DATA_SOURCE_ALL = "全量"
DATA_SOURCE_MY = "自选"
DATA_SOURCE_UPLOAD = "附件导入"


def _get_stock_info_cls():
    from aitrader.a_self_Strategy.untils.stocks_Info import Stock_Info
    return Stock_Info


@dataclass
class LongTermResult:
    success: bool
    data_source: str
    generated_at: str
    rows: List[Dict[str, Any]]
    errors: List[str]
    summary: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "data_source": self.data_source,
            "generated_at": self.generated_at,
            "rows": self.rows,
            "errors": self.errors,
            "summary": self.summary,
        }


class LongTermInvestmentService:
    """
    长线投资筛选：
    - 股性评分 > 50
    - 名称不含 ST，排除科创板/创业板/北交所
    - PE > 0 and <= 30
    - 近 1 年 ROE > 10
    - PEG < 1
    - 近 3 年营业收入同比增长 >= 15%
    """

    def __init__(self):
        self.max_workers = 6
        self.max_financial_candidates = 80
        self._financial_abstract_cache: Dict[str, Optional[pd.DataFrame]] = {}
        self._uploaded_excel_cache: Dict[str, pd.DataFrame] = {}

    def screen(
        self,
        data_source: str = DATA_SOURCE_ALL,
        limit: int = 50,
        uploaded_file: Any = None,
    ) -> Dict[str, Any]:
        generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        errors: List[str] = []
        rows: List[Dict[str, Any]] = []

        try:
            base_df = self._get_stock_pool(data_source, uploaded_file=uploaded_file)
        except Exception as exc:
            logger.exception("获取长线投资股票池失败: %s", exc)
            return LongTermResult(
                success=False,
                data_source=data_source,
                generated_at=generated_at,
                rows=[],
                errors=[f"获取股票池失败: {exc}"],
                summary={"pool_size": 0, "qualified_count": 0},
            ).to_dict()

        pool_size = len(base_df)
        logger.info("[长线投资] 股票池 %s 共 %s 只", data_source, pool_size)

        prefiltered_df = self._prefilter_candidates(base_df, data_source=data_source)
        prefiltered_count = len(prefiltered_df)

        candidate_rows = prefiltered_df.to_dict("records")
        if candidate_rows:
            if data_source == DATA_SOURCE_ALL:
                dynamic_max = max(int(limit) * 2, int(limit) + 20, 40)
                dynamic_max = min(dynamic_max, self.max_financial_candidates)
                if len(candidate_rows) > dynamic_max:
                    candidate_rows = candidate_rows[:dynamic_max]

            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                future_map = {
                    executor.submit(self._build_stock_result, row=pd.Series(row), data_source=data_source): row
                    for row in candidate_rows
                }
                for future in as_completed(future_map):
                    row = future_map[future]
                    stock_code = str(row.get("代码", "")).strip()
                    try:
                        screened = future.result()
                        if screened:
                            rows.append(screened)
                    except Exception as exc:
                        msg = f"{stock_code} 筛选异常: {exc}"
                        logger.warning(msg)
                        errors.append(msg)

        rows.sort(key=lambda item: item.get("综合评分", 0), reverse=True)
        if limit > 0:
            rows = rows[:limit]

        return LongTermResult(
            success=True,
            data_source=data_source,
            generated_at=generated_at,
            rows=rows,
            errors=errors,
            summary={
                "pool_size": pool_size,
                "prefiltered_count": prefiltered_count,
                "financial_checked_count": len(candidate_rows),
                "qualified_count": len(rows),
                "rules": self._build_rules_description(data_source),
            },
        ).to_dict()

    def _get_stock_pool(self, data_source: str, uploaded_file: Any = None) -> pd.DataFrame:
        errors: List[str] = []

        if data_source == DATA_SOURCE_UPLOAD:
            uploaded_df = self._load_uploaded_stock_dataframe(uploaded_file)
            if uploaded_df is not None and not uploaded_df.empty:
                logger.info("[长线投资] 股票池来源: 附件导入字段直连")
                return self._filter_base_pool(uploaded_df, data_source, allow_partial_fields=True, uploaded_file=uploaded_file)

        # 1. AKShare 直连实时行情，失败则继续降级
        try:
            stock_spot = ak.stock_zh_a_spot_em()
            df = self._normalize_pool_df(stock_spot)
            if df is not None and not df.empty:
                logger.info("[长线投资] 股票池来源: akshare stock_zh_a_spot_em")
                return self._filter_base_pool(df, data_source, uploaded_file=uploaded_file)
            errors.append("AKShare 返回空数据")
        except Exception as exc:
            msg = f"AKShare 股票池失败: {exc}"
            logger.warning(msg)
            errors.append(msg)

        # 2. 复用现有 data_source_manager + Tushare 降级
        try:
            df = self._build_pool_from_tushare()
            if df is not None and not df.empty:
                logger.info("[长线投资] 股票池来源: tushare daily_basic + stock_basic")
                return self._filter_base_pool(df, data_source, uploaded_file=uploaded_file)
            errors.append("Tushare 返回空数据")
        except Exception as exc:
            msg = f"Tushare 股票池失败: {exc}"
            logger.warning(msg)
            errors.append(msg)

        # 3. 自选/附件导入再兜底：仅返回基本池，允许没有估值/风格字段，后续由财务规则继续过滤
        if data_source in (DATA_SOURCE_MY, DATA_SOURCE_UPLOAD):
            df = self._build_pool_from_stock_list(data_source, uploaded_file=uploaded_file)
            if df is not None and not df.empty:
                logger.info("[长线投资] 股票池来源: %s 降级", data_source)
                return self._filter_base_pool(df, data_source, allow_partial_fields=True)

        raise ValueError("；".join(errors) if errors else "股票池获取失败")

    def _normalize_pool_df(self, stock_spot: pd.DataFrame) -> pd.DataFrame:
        if stock_spot is None or stock_spot.empty:
            raise ValueError("实时行情数据为空")

        df = stock_spot.copy()
        df["代码"] = df["代码"].astype(str)
        if "名称" not in df.columns:
            df["名称"] = ""
        df["名称"] = df["名称"].astype(str)

        for column in ["市盈率-动态", "市净率", "换手率", "振幅", "60日涨跌幅", "年初至今涨跌幅", "最新价", "涨跌幅"]:
            if column not in df.columns:
                df[column] = None
            df[column] = pd.to_numeric(df[column], errors="coerce")
        return df

    def _filter_base_pool(
        self,
        df: pd.DataFrame,
        data_source: str,
        allow_partial_fields: bool = False,
        uploaded_file: Any = None,
    ) -> pd.DataFrame:
        base_mask = (
            (~df["名称"].str.contains("ST", case=False, na=False))
            & (~df["名称"].str.contains("退市", case=False, na=False))
            & (~df["代码"].str.startswith(("688", "30", "8")))
        )
        if not allow_partial_fields:
            base_mask = base_mask & (df["市盈率-动态"] > 0) & (df["市盈率-动态"] <= 30)

        df = df[base_mask].copy()

        if data_source in (DATA_SOURCE_MY, DATA_SOURCE_UPLOAD):
            stock_list = self._resolve_stock_list(data_source=data_source, uploaded_file=uploaded_file)
            df = df[df["代码"].isin(stock_list)].copy()

        return df

    def _prefilter_candidates(self, df: pd.DataFrame, data_source: str) -> pd.DataFrame:
        if df is None or df.empty:
            return df

        work_df = df.copy()
        if data_source == DATA_SOURCE_UPLOAD:
            work_df["预估股性评分"] = 60.0
            return work_df

        work_df["预估股性评分"] = work_df.apply(self._calc_style_score, axis=1)
        work_df = work_df[work_df["预估股性评分"] > 50].copy()
        work_df = work_df.sort_values(
            by=["预估股性评分", "换手率", "60日涨跌幅", "年初至今涨跌幅"],
            ascending=False,
            na_position="last",
        )

        if data_source == DATA_SOURCE_ALL:
            work_df = work_df.head(self.max_financial_candidates).copy()
        return work_df

    def _build_pool_from_tushare(self) -> pd.DataFrame:
        ts_api = getattr(data_source_manager, "tushare_api", None)
        if ts_api is None:
            raise ValueError("未配置可用的 Tushare 数据源")

        stock_basic = ts_api.stock_basic(exchange="", list_status="L", fields="ts_code,symbol,name,market")
        daily_basic = ts_api.daily_basic(
            trade_date=datetime.now().strftime("%Y%m%d"),
            fields="ts_code,pe,pb,turnover_rate,total_mv,circ_mv",
        )

        if stock_basic is None or stock_basic.empty:
            raise ValueError("Tushare stock_basic 为空")
        if daily_basic is None or daily_basic.empty:
            raise ValueError("Tushare daily_basic 为空")

        stock_basic = stock_basic.copy()
        stock_basic["代码"] = stock_basic["symbol"].astype(str)
        stock_basic["名称"] = stock_basic["name"].astype(str)

        daily_basic = daily_basic.copy()
        daily_basic["代码"] = daily_basic["ts_code"].astype(str).str.split(".").str[0]
        daily_basic = daily_basic.rename(
            columns={
                "pe": "市盈率-动态",
                "pb": "市净率",
                "turnover_rate": "换手率",
                "total_mv": "总市值",
                "circ_mv": "流通市值",
            }
        )

        merged = pd.merge(
            stock_basic[["代码", "名称", "market"]],
            daily_basic[["代码", "市盈率-动态", "市净率", "换手率", "总市值", "流通市值"]],
            on="代码",
            how="left",
        )
        if "振幅" not in merged.columns:
            merged["振幅"] = None
        if "60日涨跌幅" not in merged.columns:
            merged["60日涨跌幅"] = None
        if "年初至今涨跌幅" not in merged.columns:
            merged["年初至今涨跌幅"] = None
        if "最新价" not in merged.columns:
            merged["最新价"] = None
        if "涨跌幅" not in merged.columns:
            merged["涨跌幅"] = None
        return self._normalize_pool_df(merged)

    def _build_pool_from_stock_list(self, data_source: str, uploaded_file: Any = None) -> pd.DataFrame:
        stock_codes = self._resolve_stock_list(data_source=data_source, uploaded_file=uploaded_file)
        if not stock_codes:
            raise ValueError(f"{data_source}为空")

        rows = []
        for code in stock_codes:
            try:
                info = data_source_manager.get_stock_basic_info(str(code))
            except Exception:
                info = {"symbol": str(code), "name": str(code)}
            rows.append(
                {
                    "代码": str(code),
                    "名称": str(info.get("name") or code),
                    "市盈率-动态": None,
                    "市净率": None,
                    "换手率": None,
                    "振幅": None,
                    "60日涨跌幅": None,
                    "年初至今涨跌幅": None,
                    "最新价": None,
                    "涨跌幅": None,
                }
            )
        return self._normalize_pool_df(pd.DataFrame(rows))

    def _resolve_stock_list(self, data_source: str, uploaded_file: Any = None) -> List[str]:
        if data_source == DATA_SOURCE_MY:
            stock_list = _get_stock_info_cls().my_stock_from_excel() or []
            return [str(code).strip() for code in stock_list if str(code).strip()]
        if data_source == DATA_SOURCE_UPLOAD:
            return self._load_uploaded_stock_codes(uploaded_file)
        return []

    def _load_uploaded_stock_codes(self, uploaded_file: Any) -> List[str]:
        normalized_df = self._load_uploaded_stock_dataframe(uploaded_file)
        stock_codes = normalized_df["代码"].astype(str).tolist() if "代码" in normalized_df.columns else []
        deduped_codes = [code for code in dict.fromkeys(stock_codes) if code]
        if not deduped_codes:
            raise ValueError(f"附件中未解析到有效股票代码: {getattr(uploaded_file, 'name', 'uploaded.xlsx')}")
        logger.info("[长线投资] 附件导入解析 %s 只股票: %s", len(deduped_codes), getattr(uploaded_file, "name", "uploaded.xlsx"))
        return deduped_codes

    def _load_uploaded_stock_dataframe(self, uploaded_file: Any) -> pd.DataFrame:
        if uploaded_file is None:
            raise ValueError("请选择要分析的附件 Excel 文件")

        file_name = getattr(uploaded_file, "name", "uploaded.xlsx")
        if file_name in self._uploaded_excel_cache:
            return self._uploaded_excel_cache[file_name].copy()

        file_bytes = uploaded_file.getvalue() if hasattr(uploaded_file, "getvalue") else uploaded_file.read()
        if not file_bytes:
            raise ValueError(f"附件文件为空: {file_name}")

        df = pd.read_excel(io.BytesIO(file_bytes), engine="openpyxl")
        if df is None or df.empty:
            raise ValueError(f"附件文件无有效数据: {file_name}")

        normalized_df = self._normalize_uploaded_dataframe(df, file_name=file_name)
        self._uploaded_excel_cache[file_name] = normalized_df.copy()
        return normalized_df

    def _normalize_uploaded_dataframe(self, df: pd.DataFrame, file_name: str) -> pd.DataFrame:
        code_col = self._pick_first_column(df, ["股票代码", "代码", "证券代码", "stock_code"])
        if code_col is None:
            raise ValueError(f"附件缺少股票代码列: {file_name}")

        name_col = self._pick_first_column(df, ["股票简称", "名称", "证券简称", "stock_name"])
        working_df = df.copy()
        working_df["代码"] = working_df[code_col].apply(self._normalize_stock_code)
        if name_col:
            working_df["名称"] = working_df[name_col].astype(str).str.strip()
        else:
            working_df["名称"] = ""

        working_df = working_df[working_df["代码"].astype(str).str.len() == 6].copy()
        working_df = working_df[~working_df["代码"].str.startswith(("688", "30", "8"))].copy()
        working_df = working_df[~working_df["名称"].str.contains("数据来源于", na=False)].copy()
        working_df = working_df[~working_df["名称"].str.lower().isin(["undefined", "none", "nan"])].copy()

        pe_col = self._find_partial_column(working_df, ["市盈率(pe)", "市盈率（pe）", "市盈率"])
        peg_col = self._find_partial_column(working_df, ["peg"])
        roe_col = self._find_partial_column(working_df, ["加权净资产收益率", "净资产收益率roe", "roe"])
        profit_score_col = self._find_partial_column(working_df, ["盈利能力评分"])
        board_col = self._find_partial_column(working_df, ["上市板块"])
        growth_cols = self._find_partial_columns(working_df, ["营业收入同比增长率"])
        growth_cols = self._sort_period_columns_desc(growth_cols)

        if pe_col:
            working_df["市盈率-动态"] = working_df[pe_col].apply(self._parse_number)
        if peg_col:
            working_df["PEG附件值"] = working_df[peg_col].apply(self._parse_number)
        if roe_col:
            working_df["ROE附件值"] = working_df[roe_col].apply(self._parse_number)
        if profit_score_col:
            working_df["盈利能力评分附件值"] = working_df[profit_score_col].apply(self._parse_number)
        if board_col:
            working_df["上市板块"] = working_df[board_col].astype(str).str.strip()

        for idx, growth_col in enumerate(growth_cols[:3], start=1):
            working_df[f"营收增长附件值_{idx}"] = working_df[growth_col].apply(self._parse_number)

        if "换手率" not in working_df.columns:
            working_df["换手率"] = None
        if "振幅" not in working_df.columns:
            working_df["振幅"] = None
        if "60日涨跌幅" not in working_df.columns:
            working_df["60日涨跌幅"] = None
        if "年初至今涨跌幅" not in working_df.columns:
            working_df["年初至今涨跌幅"] = None
        if "最新价" not in working_df.columns:
            latest_price_col = self._find_partial_column(working_df, ["现价"])
            if latest_price_col:
                working_df["最新价"] = working_df[latest_price_col].apply(self._parse_number)
            else:
                working_df["最新价"] = None
        if "涨跌幅" not in working_df.columns:
            change_col = self._find_partial_column(working_df, ["涨跌幅"])
            if change_col:
                working_df["涨跌幅"] = working_df[change_col].apply(self._parse_number)
            else:
                working_df["涨跌幅"] = None

        working_df = working_df.drop_duplicates(subset=["代码"], keep="first").reset_index(drop=True)
        if working_df.empty:
            raise ValueError(f"附件中未解析到有效股票代码: {file_name}")
        return working_df

    def _pick_first_column(self, df: pd.DataFrame, candidates: List[str]) -> Optional[str]:
        normalized = {str(col).strip(): col for col in df.columns}
        for candidate in candidates:
            if candidate in normalized:
                return normalized[candidate]
        return None

    def _find_partial_column(self, df: pd.DataFrame, keywords: List[str]) -> Optional[str]:
        for column in df.columns:
            column_text = str(column).strip().lower()
            if any(keyword.lower() in column_text for keyword in keywords):
                return column
        return None

    def _find_partial_columns(self, df: pd.DataFrame, keywords: List[str]) -> List[str]:
        matched: List[str] = []
        for column in df.columns:
            column_text = str(column).strip().lower()
            if any(keyword.lower() in column_text for keyword in keywords):
                matched.append(column)
        return matched

    def _sort_period_columns_desc(self, columns: List[str]) -> List[str]:
        def _period_key(column: str) -> str:
            text = str(column)
            match = re.search(r"(\d{4}[.\-]\d{2}[.\-]\d{2}|\d{4}[.\-]\d{2}|\d{4})", text)
            if match:
                return match.group(1).replace(".", "").replace("-", "")
            return text

        return sorted(columns, key=_period_key, reverse=True)

    def _normalize_stock_code(self, value: Any) -> str:
        text = str(value or "").strip().upper()
        if not text or text in {"NAN", "NONE", "UNDEFINED"}:
            return ""
        match = re.search(r"(\d{6})", text)
        if match:
            return match.group(1)
        return ""

    def _build_stock_result(self, row: pd.Series, data_source: str) -> Optional[Dict[str, Any]]:
        stock_code = str(row.get("代码"))
        stock_name = str(row.get("名称"))

        pe_value = self._safe_float(row.get("市盈率-动态"))
        style_score = 60.0 if data_source == DATA_SOURCE_UPLOAD else self._calc_style_score(row)

        if style_score <= 50:
            return None
        if pe_value is None or pe_value <= 0 or pe_value > 30:
            return None

        financial = self._fetch_financial_snapshot(
            stock_code,
            latest_pe=pe_value,
            row=row if data_source == DATA_SOURCE_UPLOAD else None,
        )
        if not financial:
            return None

        roe = financial.get("roe")
        peg = financial.get("peg")
        revenue_growth = financial.get("revenue_growth_3y", [])
        profit_flag = financial.get("profitability_good", False)

        roe_threshold = 8 if data_source == DATA_SOURCE_UPLOAD else 10
        peg_threshold = 1.2 if data_source == DATA_SOURCE_UPLOAD else 1
        required_growth_years = 2 if data_source == DATA_SOURCE_UPLOAD else 3
        growth_threshold = 10 if data_source == DATA_SOURCE_UPLOAD else 15

        if roe is None or roe <= roe_threshold:
            return None
        if peg is None or peg >= peg_threshold:
            return None
        if len(revenue_growth) < required_growth_years or any(growth < growth_threshold for growth in revenue_growth[:required_growth_years]):
            return None
        if not profit_flag:
            return None

        valuation_score = self._calc_valuation_score(pe_value)
        profitability_score = self._calc_profitability_score(roe, financial.get("net_margin"), financial.get("gross_margin"))
        growth_score = self._calc_growth_score(revenue_growth)
        peg_score = self._calc_peg_score(peg)
        total_score = round(style_score * 0.35 + valuation_score * 0.15 + profitability_score * 0.2 + growth_score * 0.2 + peg_score * 0.1, 2)

        hit_rules = [
            "股性评分>50",
            "非ST/非科创板/非创业板/非北交所",
            "PE<=30",
            f"ROE>{roe_threshold}%",
            f"PEG<{peg_threshold}",
            f"近{required_growth_years}期营收增速>={growth_threshold}%",
            "盈利能力优秀",
        ]

        return {
            "代码": stock_code,
            "名称": stock_name,
            "数据源": data_source,
            "股性评分": round(style_score, 2),
            "PE": pe_value,
            "ROE": round(roe, 2),
            "PEG": round(peg, 2),
            "近3年营收增速": ", ".join(f"{round(item, 2)}%" for item in revenue_growth[:3]),
            "综合评分": total_score,
            "估值评分": round(valuation_score, 2),
            "盈利评分": round(profitability_score, 2),
            "成长评分": round(growth_score, 2),
            "PEG评分": round(peg_score, 2),
            "净利率": financial.get("net_margin"),
            "毛利率": financial.get("gross_margin"),
            "命中条件说明": "；".join(hit_rules),
            "数据完整性": financial.get("data_integrity", "完整"),
        }

    def _build_rules_description(self, data_source: str) -> List[str]:
        if data_source == DATA_SOURCE_UPLOAD:
            return [
                "股性评分 > 50（附件结果集默认已满足）",
                "非ST，排除科创板/创业板/北交所",
                "PE > 0 且 <= 30",
                "近1年 ROE > 8%",
                "PEG < 1.2",
                "近2期营收同比增长均 >= 10%",
                "盈利能力评分 >= 2 或附件未提供该字段",
            ]
        return [
            "股性评分 > 50",
            "非ST，排除科创板/创业板/北交所",
            "PE > 0 且 <= 30",
            "近1年 ROE > 10%",
            "PEG < 1",
            "近3年营收同比增长均 >= 15%",
        ]

    def _fetch_financial_snapshot(
        self,
        stock_code: str,
        latest_pe: Optional[float] = None,
        row: Optional[pd.Series] = None,
    ) -> Optional[Dict[str, Any]]:
        uploaded_snapshot = self._build_financial_snapshot_from_uploaded_row(row=row, latest_pe=latest_pe)
        if uploaded_snapshot:
            return uploaded_snapshot

        abstract_df = self._get_financial_abstract(stock_code)
        if abstract_df is None or abstract_df.empty:
            return None

        period_columns = [col for col in abstract_df.columns if col not in ["选项", "指标"]]
        if not period_columns:
            return None

        latest_period = period_columns[0]
        roe = self._extract_abstract_period_value(abstract_df, latest_period, ["净资产收益率(ROE)", "净资产收益率", "ROE"])
        net_margin = self._extract_abstract_period_value(abstract_df, latest_period, ["销售净利率"])
        gross_margin = self._extract_abstract_period_value(abstract_df, latest_period, ["毛利率", "销售毛利率"])

        revenue_growth = self._extract_revenue_growth_from_abstract(abstract_df, period_columns)
        if latest_pe is None:
            latest_pe = self._extract_numeric_from_income_or_none(stock_code)
        peg = self._estimate_peg(latest_pe=latest_pe, revenue_growth=revenue_growth)

        profitability_good = bool(roe is not None and roe > 10 and ((net_margin is None or net_margin >= 10) and (gross_margin is None or gross_margin >= 20)))
        data_integrity = "完整"
        if net_margin is None or gross_margin is None:
            data_integrity = "部分字段缺失(利润率使用降级口径)"

        return {
            "roe": roe,
            "net_margin": net_margin,
            "gross_margin": gross_margin,
            "peg": peg,
            "revenue_growth_3y": revenue_growth,
            "profitability_good": profitability_good,
            "data_integrity": data_integrity,
        }

    def _build_financial_snapshot_from_uploaded_row(
        self,
        row: Optional[pd.Series],
        latest_pe: Optional[float] = None,
    ) -> Optional[Dict[str, Any]]:
        if row is None:
            return None

        roe = self._safe_float(row.get("ROE附件值"))
        peg = self._safe_float(row.get("PEG附件值"))
        profit_score = self._safe_float(row.get("盈利能力评分附件值"))
        revenue_growth = [
            self._safe_float(row.get("营收增长附件值_1")),
            self._safe_float(row.get("营收增长附件值_2")),
            self._safe_float(row.get("营收增长附件值_3")),
        ]
        revenue_growth = [value for value in revenue_growth if value is not None]

        if latest_pe is None:
            latest_pe = self._safe_float(row.get("市盈率-动态"))
        if peg is None and latest_pe is not None and revenue_growth:
            peg = self._estimate_peg(latest_pe=latest_pe, revenue_growth=revenue_growth)

        if roe is None and peg is None and not revenue_growth and profit_score is None:
            return None

        profitability_good = bool(roe is not None and roe > 8 and (profit_score is None or profit_score >= 2))
        data_integrity = "附件字段口径"
        if roe is None or peg is None or len(revenue_growth) < 3:
            data_integrity = "附件字段部分缺失"

        return {
            "roe": roe,
            "net_margin": None,
            "gross_margin": None,
            "peg": peg,
            "revenue_growth_3y": revenue_growth,
            "profitability_good": profitability_good,
            "data_integrity": data_integrity,
        }

    def _get_financial_abstract(self, stock_code: str) -> Optional[pd.DataFrame]:
        if stock_code in self._financial_abstract_cache:
            return self._financial_abstract_cache[stock_code]
        try:
            df = ak.stock_financial_abstract(symbol=stock_code)
        except Exception:
            df = None
        self._financial_abstract_cache[stock_code] = df
        return df

    def _extract_abstract_period_value(self, df: pd.DataFrame, period: str, keys: List[str]) -> Optional[float]:
        if df is None or df.empty or period not in df.columns or "指标" not in df.columns:
            return None
        for key in keys:
            matched = df[df["指标"].astype(str) == key]
            if not matched.empty:
                return self._parse_number(matched.iloc[0].get(period))
        return None

    def _extract_revenue_growth_from_abstract(self, df: pd.DataFrame, period_columns: List[str]) -> List[float]:
        if df is None or df.empty:
            return []

        revenue_row = None
        for key in ["营业总收入", "营业收入"]:
            matched = df[df["指标"].astype(str) == key]
            if not matched.empty:
                revenue_row = matched.iloc[0]
                break
        if revenue_row is None:
            return []

        annual_periods = [period for period in period_columns if str(period).endswith("1231")]
        revenues: List[float] = []
        for period in annual_periods[:4]:
            revenue_value = self._parse_number(revenue_row.get(period))
            if revenue_value is not None:
                revenues.append(revenue_value)

        growth_list: List[float] = []
        for idx in range(len(revenues) - 1):
            current_value = revenues[idx]
            last_value = revenues[idx + 1]
            if last_value and last_value > 0:
                growth_list.append((current_value - last_value) / last_value * 100)
        return growth_list

    def _extract_revenue_growth(self, income_data: List[Dict[str, Any]]) -> List[float]:
        yearly_rows: List[Dict[str, Any]] = []
        for item in income_data:
            period = str(item.get("报告期", ""))
            if period.endswith("12-31") or period.endswith("12/31"):
                yearly_rows.append(item)
            if len(yearly_rows) >= 4:
                break

        revenues: List[float] = []
        for item in yearly_rows:
            revenue = self._extract_numeric_value(item, ["营业总收入", "营业收入"])
            if revenue is not None:
                revenues.append(revenue)

        growth_list: List[float] = []
        for idx in range(len(revenues) - 1):
            current_value = revenues[idx]
            last_value = revenues[idx + 1]
            if last_value and last_value > 0:
                growth_list.append((current_value - last_value) / last_value * 100)
        return growth_list

    def _estimate_peg(self, latest_pe: Optional[float], revenue_growth: List[float]) -> Optional[float]:
        if latest_pe is None or latest_pe <= 0:
            return None
        if not revenue_growth:
            return None
        avg_growth = sum(revenue_growth[:3]) / min(len(revenue_growth), 3)
        if avg_growth <= 0:
            return None
        return latest_pe / avg_growth

    def _calc_style_score(self, row: pd.Series) -> float:
        turnover = self._safe_float(row.get("换手率")) or 0
        amplitude = self._safe_float(row.get("振幅")) or 0
        rise_60 = self._safe_float(row.get("60日涨跌幅")) or 0
        rise_ytd = self._safe_float(row.get("年初至今涨跌幅")) or 0

        score = 40
        score += min(turnover, 12) * 2.0
        score += min(amplitude, 15) * 1.5
        score += max(min(rise_60, 60), -20) * 0.5
        score += max(min(rise_ytd, 60), -20) * 0.3
        return max(0, min(100, score))

    def _calc_valuation_score(self, pe_value: Optional[float]) -> float:
        if pe_value is None:
            return 0
        return max(0, min(100, 100 - (pe_value / 30.0 * 100) + 20))

    def _calc_profitability_score(self, roe: Optional[float], net_margin: Optional[float], gross_margin: Optional[float]) -> float:
        score = 0.0
        if roe is not None:
            score += min(roe, 30) / 30 * 60
        if net_margin is not None:
            score += min(net_margin, 20) / 20 * 20
        if gross_margin is not None:
            score += min(gross_margin, 40) / 40 * 20
        return min(score, 100)

    def _calc_growth_score(self, revenue_growth: List[float]) -> float:
        if not revenue_growth:
            return 0
        avg_growth = sum(revenue_growth[:3]) / min(3, len(revenue_growth))
        return max(0, min(100, avg_growth * 2.5))

    def _calc_peg_score(self, peg: Optional[float]) -> float:
        if peg is None:
            return 0
        return max(0, min(100, (1.2 - peg) / 1.2 * 100))

    def _extract_percent_value(self, row: Dict[str, Any], keys: List[str]) -> Optional[float]:
        value = self._extract_raw_value(row, keys)
        return self._parse_number(value)

    def _extract_numeric_value(self, row: Dict[str, Any], keys: List[str]) -> Optional[float]:
        value = self._extract_raw_value(row, keys)
        return self._parse_number(value)

    def _extract_raw_value(self, row: Dict[str, Any], keys: List[str]) -> Any:
        for key in keys:
            if key in row and str(row.get(key)).strip() not in {"", "N/A", "nan", "None"}:
                return row.get(key)
        return None

    def _extract_numeric_from_income_or_none(self, stock_code: str) -> Optional[float]:
        try:
            quotes = data_source_manager.get_realtime_quotes(stock_code)
            if not quotes:
                return None
            return self._safe_float(quotes.get("pe") or quotes.get("市盈率-动态"))
        except Exception:
            return None

    def _safe_float(self, value: Any) -> Optional[float]:
        try:
            if value is None:
                return None
            if isinstance(value, str):
                value = value.replace(",", "").replace("%", "").strip()
                if not value or value.lower() in {"nan", "none", "n/a", "--"}:
                    return None
            return float(value)
        except Exception:
            return None

    def _parse_number(self, value: Any) -> Optional[float]:
        if value is None:
            return None
        if isinstance(value, (int, float)):
            if math.isnan(value) if isinstance(value, float) else False:
                return None
            return float(value)
        text = str(value)
        text = text.replace(",", "").replace("%", "").strip()
        if not text or text.lower() in {"nan", "none", "n/a", "--"}:
            return None
        matched = re.findall(r"-?\d+\.?\d*", text)
        if not matched:
            return None
        try:
            return float(matched[0])
        except Exception:
            return None
