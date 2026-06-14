#!/bin/bash

###############################################################################
# AI分析系统 - 一键部署脚本
#
# 功能：
#   1. 检查环境
#   2. 自动配置Docker镜像源
#   3. 构建并启动服务
#   4. 验证部署结果
#
# 使用方法：
#   chmod +x deploy.sh
#   sudo ./deploy.sh
###############################################################################

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 打印横幅
print_banner() {
    echo -e "${CYAN}"
    echo "╔════════════════════════════════════════════════════════╗"
    echo "║                                                        ║"
    echo "║          AI分析系统 - 一键部署脚本                ║"
    echo "║                                                        ║"
    echo "║          AI Stock Analysis System Deployer            ║"
    echo "║                                                        ║"
    echo "╚════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    echo ""
}

# 打印步骤
print_step() {
    echo -e "${BLUE}[步骤 $1/$2]${NC} $3"
}

# 打印成功
print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

# 打印错误
print_error() {
    echo -e "${RED}✗${NC} $1"
}

# 打印警告
print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# 打印信息
print_info() {
    echo -e "${CYAN}ℹ${NC} $1"
}

# 检查是否为root
check_root() {
    if [ "$EUID" -ne 0 ]; then
        print_warning "建议使用root权限运行此脚本"
        echo "请使用: sudo ./deploy.sh"
        read -p "是否继续？(y/n): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
        SUDO="sudo"
    else
        SUDO=""
    fi
}

# 检查Docker
check_docker() {
    print_step 1 6 "检查Docker环境"

    if ! command -v docker &> /dev/null; then
        print_error "Docker未安装"
        echo ""
        print_info "安装Docker..."
        curl -fsSL https://get.docker.com -o get-docker.sh
        $SUDO sh get-docker.sh
        $SUDO usermod -aG docker $USER
        print_success "Docker安装完成"
    else
        print_success "Docker已安装 ($(docker --version))"
    fi

    # 检查Docker Compose
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        print_warning "Docker Compose未安装"
        print_info "安装Docker Compose..."
        $SUDO apt-get update
        $SUDO apt-get install -y docker-compose-plugin
        print_success "Docker Compose安装完成"
    else
        print_success "Docker Compose已安装"
    fi

    echo ""
}

# 配置镜像源
setup_mirrors() {
    print_step 2 6 "配置Docker镜像源"

    if [ -f /etc/docker/daemon.json ]; then
        if grep -q "registry-mirrors" /etc/docker/daemon.json; then
            print_success "镜像源已配置"
            echo ""
            return
        fi
    fi

    print_info "配置国内镜像源..."

    # 备份原配置
    if [ -f /etc/docker/daemon.json ]; then
        $SUDO cp /etc/docker/daemon.json /etc/docker/daemon.json.backup.$(date +%Y%m%d_%H%M%S)
        print_info "已备份原配置"
    fi

    # 创建配置
    $SUDO mkdir -p /etc/docker
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

    # 重启Docker
    $SUDO systemctl daemon-reload
    $SUDO systemctl restart docker
    sleep 2

    if $SUDO systemctl is-active --quiet docker; then
        print_success "镜像源配置完成"
    else
        print_error "Docker重启失败"
        exit 1
    fi

    echo ""
}

# 创建目录
create_directories() {
    print_step 3 6 "创建必要目录"

    mkdir -p data/output/json data/output/excel data/input/myStock data/instruments log config

    print_success "目录创建完成"
    echo ""
}

# 检查配置文件
check_config() {
    print_step 4 6 "检查配置文件"

    if [ ! -f "config/config.json" ]; then
        print_warning "config/config.json 不存在"
        if [ -f "config/config.proxy.example.json" ]; then
            cp config/config.proxy.example.json config/config.json
            print_info "已复制示例配置文件"
        fi
    else
        print_success "配置文件已存在"
    fi

    echo ""
}

# 构建镜像
build_image() {
    print_step 5 6 "构建Docker镜像"

    print_info "开始构建镜像（这可能需要几分钟）..."
    echo ""

    if docker compose version &> /dev/null; then
        if docker compose build; then
            print_success "镜像构建成功"
        else
            print_error "镜像构建失败"
            exit 1
        fi
    else
        if docker-compose build; then
            print_success "镜像构建成功"
        else
            print_error "镜像构建失败"
            exit 1
        fi
    fi

    echo ""
}

# 启动服务
start_service() {
    print_step 6 6 "启动服务"

    # 停止旧容器
    docker-compose down 2>/dev/null || docker compose down 2>/dev/null || true

    # 启动新容器
    if docker compose version &> /dev/null; then
        docker compose up -d
    else
        docker-compose up -d
    fi

    # 等待启动
    print_info "等待服务启动..."
    sleep 5

    # 检查状态
    if docker ps | grep -q aiagents-stockinfo; then
        print_success "服务启动成功"
    else
        print_error "服务启动失败"
        print_info "查看日志: docker logs aiagents-stockinfo"
        exit 1
    fi

    echo ""
}

# 显示结果
show_result() {
    echo -e "${GREEN}"
    echo "╔════════════════════════════════════════════════════════╗"
    echo "║                                                        ║"
    echo "║                 🎉 部署成功！🎉                        ║"
    echo "║                                                        ║"
    echo "╚════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    echo ""

    echo -e "${CYAN}访问地址：${NC}"
    echo "  🌐 本地: http://localhost:8501"

    if command -v hostname &> /dev/null; then
        LOCAL_IP=$(hostname -I 2>/dev/null | awk '{print $1}')
        if [ ! -z "$LOCAL_IP" ]; then
            echo "  🌐 远程: http://${LOCAL_IP}:8501"
        fi
    fi

    echo ""
    echo -e "${CYAN}常用命令：${NC}"
    echo "  📊 查看日志: docker logs -f aiagents-stockinfo"
    echo "  🔄 重启服务: docker compose restart"
    echo "  ⏹️  停止服务: docker compose down"
    echo "  📈 查看状态: docker ps"
    echo "  🔍 查看资源: docker stats aiagents-stockinfo"
    echo ""

    echo -e "${CYAN}相关文档：${NC}"
    echo "  📖 使用说明: cat Docker使用说明.md"
    echo "  🔧 故障排查: cat QUICK_FIX.md"
    echo "  📚 完整文档: cat DOCKER_QUICK_START.md"
    echo ""
}

# 主函数
main() {
    print_banner

    check_root
    check_docker
    setup_mirrors
    create_directories
    check_config
    build_image
    start_service
    show_result

    print_success "部署完成！祝使用愉快！ 🚀"
    echo ""
}

# 执行主函数
main
