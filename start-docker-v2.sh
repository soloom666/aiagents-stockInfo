#!/bin/bash

# AI股票分析系统 - Docker启动脚本
# 用于在Linux系统上快速启动Streamlit应用

echo "========================================="
echo "  AI股票分析系统 - Docker启动"
echo "========================================="
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 检查Docker是否安装
if ! command -v docker &> /dev/null; then
    echo -e "${RED}错误: Docker未安装${NC}"
    echo "请先安装Docker: https://docs.docker.com/engine/install/"
    exit 1
fi

# 检查Docker Compose是否安装
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo -e "${RED}错误: Docker Compose未安装${NC}"
    echo "请先安装Docker Compose: https://docs.docker.com/compose/install/"
    exit 1
fi

# 创建必要的目录
echo -e "${YELLOW}创建必要的目录...${NC}"
mkdir -p data/output/json data/output/excel data/input/myStock data/instruments log config

# 检查配置文件
if [ ! -f "config/config.json" ]; then
    echo -e "${YELLOW}警告: config/config.json 不存在，将使用默认配置${NC}"
    if [ -f "config/config.proxy.example.json" ]; then
        echo "复制示例配置文件..."
        cp config/config.proxy.example.json config/config.json
    fi
fi

# 停止并移除旧容器
echo -e "${YELLOW}停止旧容器...${NC}"
docker-compose down 2>/dev/null || docker compose down 2>/dev/null || true

# 构建镜像
echo -e "${YELLOW}构建Docker镜像...${NC}"
BUILD_SUCCESS=0
if docker compose version &> /dev/null; then
    if docker compose build 2>&1; then
        BUILD_SUCCESS=1
    fi
else
    if docker-compose build 2>&1; then
        BUILD_SUCCESS=1
    fi
fi

# 检查构建是否成功
if [ $BUILD_SUCCESS -eq 0 ]; then
    echo ""
    echo -e "${RED}=========================================${NC}"
    echo -e "${RED}  ✗ 镜像构建失败${NC}"
    echo -e "${RED}=========================================${NC}"
    echo ""
    echo -e "${YELLOW}常见原因：${NC}"
    echo "  1. 无法从Docker官方源下载镜像（最常见）"
    echo "  2. 网络连接问题"
    echo "  3. Docker镜像源未配置"
    echo ""
    echo -e "${BLUE}快速解决方案：${NC}"
    echo ""
    echo -e "${GREEN}  方法一：自动配置镜像源（推荐）${NC}"
    echo "    chmod +x fix-docker-mirror.sh"
    echo "    sudo ./fix-docker-mirror.sh"
    echo ""
    echo -e "${GREEN}  方法二：手动配置${NC}"
    echo "    查看详细说明: cat Docker镜像源配置说明.md"
    echo ""
    exit 1
fi

# 启动容器
echo -e "${YELLOW}启动容器...${NC}"
if docker compose version &> /dev/null; then
    docker compose up -d
else
    docker-compose up -d
fi

# 等待服务启动
echo -e "${YELLOW}等待服务启动...${NC}"
sleep 5

# 检查容器状态
if docker ps | grep -q aiagents-stockinfo; then
    echo -e "${GREEN}=========================================${NC}"
    echo -e "${GREEN}  ✓ 启动成功！${NC}"
    echo -e "${GREEN}=========================================${NC}"
    echo ""
    echo "访问地���："
    echo "  本地: http://localhost:8501"
    if command -v hostname &> /dev/null; then
        LOCAL_IP=$(hostname -I 2>/dev/null | awk '{print $1}')
        if [ ! -z "$LOCAL_IP" ]; then
            echo "  远程: http://${LOCAL_IP}:8501"
        fi
    fi
    echo ""
    echo "常用命令："
    echo "  查看日志: docker logs -f aiagents-stockinfo"
    echo "  停止服务: docker-compose down 或 docker compose down"
    echo "  重启服务: docker-compose restart 或 docker compose restart"
    echo "  查看状态: docker ps"
    echo ""
else
    echo -e "${RED}=========================================${NC}"
    echo -e "${RED}  ✗ 启动失败${NC}"
    echo -e "${RED}=========================================${NC}"
    echo ""
    echo "请查看日志排查问题:"
    echo "  docker logs aiagents-stockinfo"
    echo ""
    echo "或查看容器状态:"
    echo "  docker ps -a | grep aiagents"
    echo ""
    exit 1
fi
