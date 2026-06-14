#!/bin/bash

# Docker镜像源配置脚本
# 解决 "load metadata for docker.io/library/python" 错误

set -e

echo "========================================="
echo "  配置Docker镜像源"
echo "========================================="
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 检查是否为root用户
if [ "$EUID" -ne 0 ]; then
    echo -e "${YELLOW}提示: 需要root权限，将使用sudo${NC}"
    SUDO="sudo"
else
    SUDO=""
fi

# 备份原配置
echo -e "${YELLOW}1. 备份原配置...${NC}"
if [ -f /etc/docker/daemon.json ]; then
    $SUDO cp /etc/docker/daemon.json /etc/docker/daemon.json.backup.$(date +%Y%m%d_%H%M%S)
    echo -e "${GREEN}✓ 已备份原配置${NC}"
else
    echo -e "${BLUE}ℹ 未发现原配置文件${NC}"
fi

# 创建新配置
echo -e "${YELLOW}2. 配置镜像源...${NC}"
$SUDO mkdir -p /etc/docker

# 写入配置
$SUDO tee /etc/docker/daemon.json > /dev/null <<EOF
{
  "registry-mirrors": [
    "https://docker.mirrors.ustc.edu.cn",
    "https://hub-mirror.c.163.com",
    "https://mirror.baidubce.com",
    "https://docker.m.daocloud.io"
  ],
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "100m",
    "max-file": "3"
  }
}
EOF

echo -e "${GREEN}✓ 配置文件已创建${NC}"

# 重启Docker服务
echo -e "${YELLOW}3. 重启Docker服务...${NC}"
$SUDO systemctl daemon-reload
$SUDO systemctl restart docker

# 等待Docker启动
sleep 3

# 验证配置
echo -e "${YELLOW}4. 验证配置...${NC}"
if $SUDO systemctl is-active --quiet docker; then
    echo -e "${GREEN}✓ Docker服务运行正常${NC}"

    # 显示配置的镜像源
    echo ""
    echo -e "${BLUE}已配置的镜像源：${NC}"
    $SUDO docker info 2>/dev/null | grep -A 10 "Registry Mirrors:" || echo "  (镜像源已配置，但info命令未显示详情)"

    echo ""
    echo -e "${GREEN}=========================================${NC}"
    echo -e "${GREEN}  ✓ 配置完成！${NC}"
    echo -e "${GREEN}=========================================${NC}"
    echo ""
    echo "现在可以重新构建镜像了："
    echo "  docker compose build"
    echo "  或者"
    echo "  ./start-docker.sh"

else
    echo -e "${RED}✗ Docker服务启动失败${NC}"
    echo "请检查日志: sudo journalctl -xeu docker"
    exit 1
fi
