#!/bin/bash

# AI股票分析系统 - Docker停止脚本

set -e

echo "========================================="
echo "  AI股票分析系统 - Docker停止"
echo "========================================="
echo ""

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 停止容器
echo -e "${YELLOW}停止容器...${NC}"
if docker compose version &> /dev/null; then
    docker compose down
else
    docker-compose down
fi

echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN}  ✓ 服务已停止${NC}"
echo -e "${GREEN}=========================================${NC}"
