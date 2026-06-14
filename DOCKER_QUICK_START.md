# 🐳 Docker 快速启动指南

本指南帮助你在Linux系统上使用Docker快速启动AI股票分析系统。

## 📋 前置要求

### 1. 安装Docker
```bash
# Ubuntu/Debian
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# 添加当前用户到docker组（避免每次使用sudo）
sudo usermod -aG docker $USER
newgrp docker
```

### 2. 安装Docker Compose
```bash
# 安装Docker Compose v2
sudo apt-get update
sudo apt-get install docker-compose-plugin

# 或安装Docker Compose v1
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

### 3. 验证安装
```bash
docker --version
docker compose version  # 或 docker-compose --version
```

## 🚀 快速启动

### 方法一：使用启动脚本（推荐）

1. **克隆或上传项目到Linux服务器**
```bash
cd /path/to/aiagents-stockInfo
```

2. **赋予脚本执行权限**
```bash
chmod +x start-docker.sh stop-docker.sh
```

3. **启动服务**
```bash
./start-docker.sh
```

启动成功后会显示访问地址。

### 方法二：使用Docker Compose命令

```bash
# 构建镜像
docker compose build
# 或 docker-compose build

# 启动容器（后台运行）
docker compose up -d
# 或 docker-compose up -d
```

### 方法三：直接使用Docker命令

```bash
# 构建镜像
docker build -t aiagents-stockinfo:latest .

# 运行容器
docker run -d \
  --name aiagents-stockinfo \
  -p 8501:8501 \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/log:/app/log \
  -v $(pwd)/config:/app/config \
  -e TZ=Asia/Shanghai \
  --restart unless-stopped \
  aiagents-stockinfo:latest
```

## 🌐 访问应用

启动成功后，可以通过以下方式访问：

### 本地访问
```
http://localhost:8501
```

### 远程访问（从其他机器）
```
http://<服务器IP>:8501
```

例如：`http://101.132.190.29:8501`

## 📊 常用命令

### 查看容器状态
```bash
docker ps
```

### 查看日志
```bash
# 实时查看日志
docker logs -f aiagents-stockinfo

# 查看最近100行日志
docker logs --tail 100 aiagents-stockinfo
```

### 停止服务
```bash
# 使用脚本
./stop-docker.sh

# 或使用docker compose
docker compose down
# 或 docker-compose down
```

### 重启服务
```bash
docker compose restart
# 或 docker-compose restart
```

### 进入容器
```bash
docker exec -it aiagents-stockinfo bash
```

### 更新服务
```bash
# 停止并删除旧容器
docker compose down

# 重新构建镜像
docker compose build --no-cache

# 启动新容器
docker compose up -d
```

## 🔧 配置说明

### 1. 环境配置

配置文件位置：
- `config/config.json` - 主配置文件
- `config/emailConfig.yaml` - 邮件配置
- `.env` - 环境变量（如API密钥）

### 2. 数据持久化

以下目录会自动挂载到宿主机，确保数据持久化：
- `./data` - 数据文件目录
- `./log` - 日志文件目录
- `./config` - 配置文件目录

### 3. 端口映射

默认端口：`8501`

如需修改端口，编辑 `docker-compose.yml`:
```yaml
ports:
  - "8080:8501"  # 改为8080端口
```

## 🛠️ 故障排查

### 1. 容器无法启动

查看容器日志：
```bash
docker logs aiagents-stockinfo
```

### 2. 端口被占用

查看端口占用：
```bash
sudo lsof -i :8501
```

杀死占用进程：
```bash
sudo kill -9 <PID>
```

或修改docker-compose.yml中的端口映射。

### 3. 依赖安装失败

如果Python包安装失败，可以尝试：

1. 使用国内镜像源（Dockerfile中已配置）
2. 修改requirements.txt，删除有问题的包
3. 重新构建镜像：
```bash
docker compose build --no-cache
```

### 4. 内存不足

编辑 `docker-compose.yml`，调整资源限制：
```yaml
deploy:
  resources:
    limits:
      memory: 2G  # 减少内存限制
```

### 5. 无法访问网络

检查防火墙设置：
```bash
# Ubuntu/Debian
sudo ufw allow 8501

# CentOS/RHEL
sudo firewall-cmd --permanent --add-port=8501/tcp
sudo firewall-cmd --reload
```

## 🔒 安全建议

### 1. 生产环境部署

如果在公网环境部署，建议：

1. **使用Nginx反向代理**，添加SSL证书
2. **配置防火墙**，限制访问IP
3. **设置认证**，保护应用访问

### 2. Nginx反向代理示例

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## 📦 资源管理

### 查看Docker资源使用
```bash
docker stats aiagents-stockinfo
```

### 清理未使用的镜像和容器
```bash
# 清理所有未使用的容器、网络、镜像
docker system prune -a

# 清理特定镜像
docker rmi aiagents-stockinfo:latest
```

## 🔄 更新升级

### 1. 更新代码
```bash
git pull origin main
```

### 2. 重新构建并启动
```bash
./start-docker.sh
```

或手动执行：
```bash
docker compose down
docker compose build --no-cache
docker compose up -d
```

## 📞 技术支持

如果遇到问题：

1. 查看日志：`docker logs -f aiagents-stockinfo`
2. 查看文档：`docs/` 目录
3. 提交Issue：GitHub Issues

---

## 🎯 快速命令参考

```bash
# 启动
./start-docker.sh

# 停止
./stop-docker.sh

# 查看日志
docker logs -f aiagents-stockinfo

# 重启
docker compose restart

# 查看状态
docker ps

# 进入容器
docker exec -it aiagents-stockinfo bash
```

---

**祝你使用愉快！** 📈🚀
