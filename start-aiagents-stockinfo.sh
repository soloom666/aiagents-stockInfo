#!/usr/bin/env bash

LOG_DIR="/opt/logs"
LOG_FILE="$LOG_DIR/streamlit.log"
PYTHON_BIN="${PYTHON_BIN:-python3}"

pkill -f "python.*-m streamlit run app.py" || true
ps aux | grep streamlit || true

nohup "$PYTHON_BIN" -m streamlit run app.py > "$LOG_FILE" 2>&1 &

echo "已启动 streamlit，使用解释器: $PYTHON_BIN，日志文件: $LOG_FILE"
