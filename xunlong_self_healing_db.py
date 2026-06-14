"""
寻龙记 AI 自愈 / 复测数据库
"""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd


class XunlongSelfHealingDB:
    def __init__(self, db_path: str = "xunlong_self_healing.db"):
        self.db_path = db_path
        self._init_db()

    def _get_conn(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS recommendation_batches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                batch_time TEXT NOT NULL,
                data_source TEXT NOT NULL,
                result_json TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS recommendation_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                batch_id INTEGER NOT NULL,
                stock_code TEXT NOT NULL,
                stock_name TEXT,
                source_tag TEXT NOT NULL,
                recommended_date TEXT NOT NULL,
                recommended_price REAL,
                review_due_date TEXT,
                review_price REAL,
                return_pct REAL,
                feedback_status TEXT,
                stock_cooldown INTEGER DEFAULT 0,
                reviewed INTEGER DEFAULT 0,
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(batch_id) REFERENCES recommendation_batches(id)
            )
            """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_feedback_reviewed
            ON recommendation_feedback(reviewed, review_due_date)
            """
        )
        conn.commit()
        conn.close()

    def save_batch(self, data_source: str, result: Dict[str, Any], stock_price_map: Dict[str, Optional[float]]) -> int:
        conn = self._get_conn()
        cursor = conn.cursor()
        batch_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute(
            """
            INSERT INTO recommendation_batches(batch_time, data_source, result_json)
            VALUES (?, ?, ?)
            """,
            (batch_time, data_source, json.dumps(result, ensure_ascii=False)),
        )
        batch_id = cursor.lastrowid

        recommended_date = datetime.now().strftime("%Y-%m-%d")
        review_due_date = self._estimate_due_date(recommended_date, 3)
        for source_tag, stocks in self._iter_source_stocks(result):
            for stock_code in stocks:
                cursor.execute(
                    """
                    INSERT INTO recommendation_feedback(
                        batch_id, stock_code, source_tag, recommended_date,
                        recommended_price, review_due_date, feedback_status, reviewed
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, 0)
                    """,
                    (
                        batch_id,
                        stock_code,
                        source_tag,
                        recommended_date,
                        stock_price_map.get(stock_code),
                        review_due_date,
                        "待复测",
                    ),
                )

        conn.commit()
        conn.close()
        return batch_id

    def list_pending_feedback(self) -> pd.DataFrame:
        conn = self._get_conn()
        query = """
        SELECT *
        FROM recommendation_feedback
        WHERE reviewed = 0
        ORDER BY recommended_date ASC, id ASC
        """
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df

    def update_feedback(
        self,
        feedback_id: int,
        review_price: Optional[float],
        return_pct: Optional[float],
        feedback_status: str,
        stock_cooldown: int,
        notes: str = "",
    ) -> None:
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE recommendation_feedback
            SET review_price = ?, return_pct = ?, feedback_status = ?, stock_cooldown = ?,
                reviewed = 1, notes = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (review_price, return_pct, feedback_status, stock_cooldown, notes, feedback_id),
        )
        conn.commit()
        conn.close()

    def get_feedback_records(self, limit: int = 100) -> pd.DataFrame:
        conn = self._get_conn()
        query = """
        SELECT rf.*, rb.batch_time, rb.data_source
        FROM recommendation_feedback rf
        JOIN recommendation_batches rb ON rb.id = rf.batch_id
        ORDER BY rf.created_at DESC
        LIMIT ?
        """
        df = pd.read_sql_query(query, conn, params=[limit])
        conn.close()
        return df

    def get_source_stats(self) -> pd.DataFrame:
        conn = self._get_conn()
        query = """
        SELECT
            source_tag,
            COUNT(*) AS total_count,
            SUM(CASE WHEN reviewed = 1 THEN 1 ELSE 0 END) AS reviewed_count,
            SUM(CASE WHEN feedback_status = '正反馈' THEN 1 ELSE 0 END) AS positive_count,
            AVG(CASE WHEN reviewed = 1 THEN return_pct END) AS avg_return_pct
        FROM recommendation_feedback
        GROUP BY source_tag
        ORDER BY avg_return_pct DESC
        """
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df

    def get_stock_penalty(self, stock_code: str) -> int:
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT COALESCE(MAX(stock_cooldown), 0)
            FROM recommendation_feedback
            WHERE stock_code = ?
            """,
            (stock_code,),
        )
        row = cursor.fetchone()
        conn.close()
        return int(row[0] or 0)

    def get_source_weight_map(self) -> Dict[str, float]:
        stats = self.get_source_stats()
        weights: Dict[str, float] = {}
        if stats.empty:
            return weights
        for _, row in stats.iterrows():
            avg_return = row.get("avg_return_pct")
            positive_count = row.get("positive_count", 0) or 0
            reviewed_count = row.get("reviewed_count", 0) or 0
            win_rate = positive_count / reviewed_count if reviewed_count else 0
            weight = 1.0 + win_rate * 0.3
            if avg_return is not None:
                weight += max(min(float(avg_return) / 100.0, 0.2), -0.2)
            weights[str(row["source_tag"])] = round(max(0.5, min(weight, 1.5)), 3)
        return weights

    def _iter_source_stocks(self, result: Dict[str, Any]):
        for source_tag in ("macd", "yaogu"):
            stocks = result.get(source_tag) or []
            if isinstance(stocks, list):
                yield source_tag, list({str(stock).strip() for stock in stocks if stock})

        al_agent = result.get("al_agent_stocks") or {}
        longhuban_stocks = al_agent.get("longhuban_stocks") or []
        if isinstance(longhuban_stocks, list):
            yield "longhubang_agent", list({str(stock).strip() for stock in longhuban_stocks if stock})

    def _estimate_due_date(self, from_date: str, trading_days: int) -> str:
        current = pd.Timestamp(from_date)
        remain = trading_days
        while remain > 0:
            current += pd.Timedelta(days=1)
            if current.weekday() < 5:
                remain -= 1
        return current.strftime("%Y-%m-%d")
