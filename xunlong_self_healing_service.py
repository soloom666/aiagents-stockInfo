"""
寻龙记 AI 自愈服务
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd

from aitrader.a_self_Strategy.untils.stocks_Info import Stock_Info
from common.logger import logger
from xunlong_self_healing_db import XunlongSelfHealingDB


class XunlongSelfHealingService:
    def __init__(self):
        self.db = XunlongSelfHealingDB()

    def record_recommendation_batch(self, result: Dict[str, Any], data_source: str = "自选") -> int:
        codes = self._collect_codes(result)
        stock_price_map = self._fetch_close_price_map(codes)
        batch_id = self.db.save_batch(data_source=data_source, result=result, stock_price_map=stock_price_map)
        logger.info("[寻龙记自愈] 已记录推荐批次 batch_id=%s, 股票数=%s", batch_id, len(codes))
        return batch_id

    def review_due_feedback(self) -> Dict[str, Any]:
        pending_df = self.db.list_pending_feedback()
        if pending_df.empty:
            return {"success": True, "reviewed_count": 0, "message": "无待复测记录"}

        today = datetime.now().strftime("%Y-%m-%d")
        reviewed_count = 0

        for _, row in pending_df.iterrows():
            due_date = str(row.get("review_due_date") or "")
            if due_date and due_date > today:
                continue

            stock_code = str(row["stock_code"])
            recommended_price = self._safe_float(row.get("recommended_price"))
            review_price = self._fetch_single_close_price(stock_code)
            if recommended_price is None or review_price is None or recommended_price <= 0:
                self.db.update_feedback(
                    feedback_id=int(row["id"]),
                    review_price=review_price,
                    return_pct=None,
                    feedback_status="复测失败",
                    stock_cooldown=0,
                    notes="价格缺失，无法计算收益",
                )
                reviewed_count += 1
                continue

            return_pct = (review_price - recommended_price) / recommended_price * 100
            feedback_status = "正反馈" if return_pct > 0 else "负反馈"
            cooldown = 1 if return_pct <= 0 else 0

            self.db.update_feedback(
                feedback_id=int(row["id"]),
                review_price=review_price,
                return_pct=return_pct,
                feedback_status=feedback_status,
                stock_cooldown=cooldown,
                notes=f"3日收益复测完成，来源={row['source_tag']}",
            )
            reviewed_count += 1

        logger.info("[寻龙记自愈] 复测完成 %s 条", reviewed_count)
        return {"success": True, "reviewed_count": reviewed_count, "message": f"复测完成 {reviewed_count} 条"}

    def get_dashboard_data(self, limit: int = 100) -> Dict[str, Any]:
        records = self.db.get_feedback_records(limit=limit)
        stats = self.db.get_source_stats()
        records = self._normalize_numeric_columns(records, ["recommended_price", "review_price", "return_pct"])
        stats = self._normalize_numeric_columns(stats, ["total_count", "reviewed_count", "positive_count", "avg_return_pct"])
        return {
            "records": records,
            "stats": stats,
            "weights": self.db.get_source_weight_map(),
        }

    def reorder_recommendations(self, result: Dict[str, Any]) -> Dict[str, Any]:
        source_weights = self.db.get_source_weight_map()
        reordered = dict(result)
        reordered["self_healing_meta"] = {
            "source_weights": source_weights,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

        for source_tag in ("macd", "yaogu"):
            stocks = reordered.get(source_tag) or []
            if not isinstance(stocks, list):
                continue
            weight = source_weights.get(source_tag, 1.0)
            reordered[source_tag] = self._sort_stock_list(stocks, weight)

        al_agent = reordered.get("al_agent_stocks") or {}
        longhuban_stocks = al_agent.get("longhuban_stocks") or []
        if isinstance(longhuban_stocks, list):
            weight = source_weights.get("longhubang_agent", 1.0)
            al_agent["longhuban_stocks"] = self._sort_stock_list(longhuban_stocks, weight)
            reordered["al_agent_stocks"] = al_agent

        return reordered

    def _sort_stock_list(self, stocks: List[str], source_weight: float) -> List[str]:
        unique_stocks = list({str(stock).strip() for stock in stocks if stock})
        scored = []
        for stock_code in unique_stocks:
            penalty = self.db.get_stock_penalty(stock_code)
            score = source_weight - penalty * 0.3
            scored.append((stock_code, score))
        scored.sort(key=lambda item: item[1], reverse=True)
        return [item[0] for item in scored]

    def _collect_codes(self, result: Dict[str, Any]) -> List[str]:
        codes: List[str] = []
        for source_tag in ("macd", "yaogu"):
            source_codes = result.get(source_tag) or []
            if isinstance(source_codes, list):
                codes.extend([str(code).strip() for code in source_codes if code])

        al_agent = result.get("al_agent_stocks") or {}
        longhuban_stocks = al_agent.get("longhuban_stocks") or []
        if isinstance(longhuban_stocks, list):
            codes.extend([str(code).strip() for code in longhuban_stocks if code])
        return list(dict.fromkeys(codes))

    def _fetch_close_price_map(self, codes: List[str]) -> Dict[str, Optional[float]]:
        price_map: Dict[str, Optional[float]] = {}
        if not codes:
            return price_map
        try:
            stock_df = Stock_Info.get_realtime_data(codes, increase=0)
            if stock_df is not None and not stock_df.empty:
                for _, row in stock_df.iterrows():
                    code = str(row.get("代码", "")).strip()
                    price_map[code] = self._safe_float(row.get("最新价") or row.get("收盘"))
        except Exception as exc:
            logger.warning("[寻龙记自愈] 批量获取价格失败: %s", exc)

        for code in codes:
            price_map.setdefault(code, self._fetch_single_close_price(code))
        return price_map

    def _fetch_single_close_price(self, stock_code: str) -> Optional[float]:
        try:
            stock_df = Stock_Info.get_realtime_data(stock_code, increase=0)
            if stock_df is None or stock_df.empty:
                return None
            row = stock_df.iloc[0]
            return self._safe_float(row.get("最新价") or row.get("收盘"))
        except Exception as exc:
            logger.warning("[寻龙记自愈] 获取 %s 价格失败: %s", stock_code, exc)
            return None

    def _safe_float(self, value: Any) -> Optional[float]:
        try:
            if value is None:
                return None
            return float(value)
        except Exception:
            return None

    def _normalize_numeric_columns(self, df: pd.DataFrame, columns: List[str]) -> pd.DataFrame:
        if df is None or df.empty:
            return df
        normalized = df.copy()
        for column in columns:
            if column in normalized.columns:
                normalized[column] = pd.to_numeric(normalized[column], errors="coerce")
        return normalized
