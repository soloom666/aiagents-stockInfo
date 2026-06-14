# 🐳 Docker部署完整清单

本文档汇总了所有Docker相关文件和使用方法。

---

## 📦 已创建的文件清单

### 核心配置文件
- ✅ `Dockerfile` - Docker镜像构建文件
- ✅ `docker-compose.yml` - Docker Compose编排文件
- ✅ `.dockerignore` - Docker构建忽略文件

### 启动脚本
- ✅ `start-docker.sh` - 标准启动脚本
- ✅ `start-docker-v2.sh` - 增强版启动脚本（带错误检测）
- ✅ `stop-docker.sh` - 停止服务脚本
- ✅ `fix-docker-mirror.sh` - 镜像源自动配置脚本

### 配置文件
- ✅ `docker-daemon-config.json` - Docker daemon配置示例
- ✅ `.env.example` - 环境变量示例

### 文档
- ✅ `QUICK_FIX.md` - 快速修复指南（镜像拉取错误）⭐
- ✅ `Docker使用说明.md` - 中文简化版使用说明
- ✅ `DOCKER_QUICK_START.md` - 详细部署文档（英文）
- ✅ `Docker镜像源配置说明.md` - 镜像源配置详细说明
- ✅ `Docker部署完整清单.md` - 本文档

---

## 🚀 快速开始（3步）

### 新手推荐流程

```bash
# 第1步：赋予执行权限
chmod +x *.sh

# 第2步：配置Docker镜像源（重要！）
sudo ./fix-docker-mirror.sh

# 第3步：启动服务
./start-docker.sh
```

访问：http://localhost:8501

---

## 🔧 常见问题解决方案

### 问题1：镜像拉取失败
```
ERROR [streamlit-app internal] load metadata for docker.io/library/python:3.11-slim
```

**解决方案：**
```bash
sudo ./fix-docker-mirror.sh
```

详见：[QUICK_FIX.md](QUICK_FIX.md)

### 问题2：端口被占用
```
Error starting userland proxy: listen tcp4 0.0.0.0:8501: bind: address already in use
```

**解决方案：**
```bash
# 方法1：查找并停止占用端口的进程
sudo lsof -i :8501
sudo kill -9 <PID>

# 方法2：修改端口
# 编辑 docker-compose.yml
ports:
  - "8080:8501"  # 改为其他端口
```

### 问题3：权限不足
```
permission denied while trying to connect to the Docker daemon socket
```

**解决方案：**
```bash
# 将当前用户添加到docker组
sudo usermod -aG docker $USER

# 重新登录或执行
newgrp docker
```

### 问题4：容器启动失败

**解决方案：**
```bash
# 查看详细日志
docker logs aiagents-stockinfo

# 查看容器状态
docker ps -a | grep aiagents

# 进入容器调试
docker exec -it aiagents-stockinfo bash
```

### 问题5：依赖安装失败

**解决方案：**
```bash
# 重新构建（清除缓存）
docker compose build --no-cache

# 或者修改 requirements.txt 删除有问题的包
```

---

## 📋 常用命令速查表

### 启动相关
| 操作 | 命令 |
|------|------|
| 一键启动 | `./start-docker.sh` |
| 使用Compose启动 | `docker compose up -d` |
| 前台启动（查看日志） | `docker compose up` |

### 查看相关
| 操作 | 命令 |
|------|------|
| 查看运行状态 | `docker ps` |
| 查看所有容器 | `docker ps -a` |
| 查看实时日志 | `docker logs -f aiagents-stockinfo` |
| 查看最近100行日志 | `docker logs --tail 100 aiagents-stockinfo` |
| 查看资源使用 | `docker stats aiagents-stockinfo` |

### 停止/重启
| 操作 | 命令 |
|------|------|
| 停止服务 | `./stop-docker.sh` 或 `docker compose down` |
| 重启服务 | `docker compose restart` |
| 重启特定容器 | `docker restart aiagents-stockinfo` |

### 维护相关
| 操作 | 命令 |
|------|------|
| 进入容器 | `docker exec -it aiagents-stockinfo bash` |
| 重新构建 | `docker compose build --no-cache` |
| 查看镜像 | `docker images` |
| 删除容器 | `docker rm aiagents-stockinfo` |
| 删除镜像 | `docker rmi aiagents-stockinfo` |
| 清理系统 | `docker system prune -a` |

---

## 🎯 不同场景的部署方案

### 场景1：开发环境（本地测试）
```bash
# 使用默认配置
./start-docker.sh

# 需要实时查看日志
docker compose up
```

### 场景2：生产环境（服务器部署）
```bash
# 1. 配置镜像源
sudo ./fix-docker-mirror.sh

# 2. 修改配置文件
cp .env.example .env
nano .env  # 填入真实的API密钥

# 3. 启动服务（后台运行）
docker compose up -d

# 4. 配置Nginx反向代理（可选，推荐）
# 参考 DOCKER_QUICK_START.md
```

### 场景3：测试环境（快速验证）
```bash
# 直接使用Docker命令
docker build -t aiagents-stockinfo .
docker run -d -p 8501:8501 aiagents-stockinfo
```

### 场景4：离线环境（无网络）
```bash
# 在有网络的机器上
docker build -t aiagents-stockinfo .
docker save aiagents-stockinfo:latest -o aiagents.tar

# 传输到离线机器
docker load -i aiagents.tar
docker run -d -p 8501:8501 aiagents-stockinfo
```

---

## 🔒 安全加固建议

### 1. 使用Nginx反向代理
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8501;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 2. 配置SSL证书
```bash
# 使用Let's Encrypt
sudo apt-get install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

### 3. 限制访问IP
```yaml
# 在 docker-compose.yml 中
services:
  streamlit-app:
    ports:
      - "127.0.0.1:8501:8501"  # 只允许本地访问
```

### 4. 设置防火墙
```bash
# 只允许特定IP访问
sudo ufw allow from 192.168.1.0/24 to any port 8501
```

---

## 📊 性能优化建议

### 1. 资源限制调整
编辑 `docker-compose.yml`:
```yaml
deploy:
  resources:
    limits:
      cpus: '4.0'      # 增加CPU
      memory: 8G       # 增加内存
```

### 2. 使用缓存加速构建
```bash
# 使用BuildKit
DOCKER_BUILDKIT=1 docker build -t aiagents-stockinfo .
```

### 3. 优化镜像大小
- 使用多阶段构建
- 清理不必要的文件
- 使用.dockerignore

---

## 🔄 更新升级流程

### 标准更新流程
```bash
# 1. 拉取最新代码
git pull

# 2. 停止旧容器
docker compose down

# 3. 重新构建
docker compose build --no-cache

# 4. 启动新容器
docker compose up -d

# 5. 验证
docker ps
docker logs -f aiagents-stockinfo
```

### 零停机更新（高级）
```bash
# 使用蓝绿部署
docker-compose -f docker-compose.blue.yml up -d
# 切换流量
docker-compose -f docker-compose.green.yml down
```

---

## 📚 文档阅读顺序

### 新手用户
1. [Docker使用说明.md](Docker使用说明.md) - 中文简化版
2. [QUICK_FIX.md](QUICK_FIX.md) - 遇到问题时查看
3. 本文档 - 了解全貌

### 进阶用户
1. [DOCKER_QUICK_START.md](DOCKER_QUICK_START.md) - 详细部署文档
2. [Docker镜像源配置说明.md](Docker镜像源配置说明.md) - 深入了解配置
3. 本文档 - 查看高级用法

### 运维人员
1. 本文档 - 全面了解
2. [DOCKER_QUICK_START.md](DOCKER_QUICK_START.md) - 生产环境部署
3. 官方Docker文档 - 深入学习

---

## 🆘 获取帮助

### 问题诊断步骤

1. **检查Docker服务状态**
   ```bash
   sudo systemctl status docker
   ```

2. **查看容器日志**
   ```bash
   docker logs aiagents-stockinfo
   ```

3. **检查网络连接**
   ```bash
   docker network ls
   docker network inspect bridge
   ```

4. **验证镜像**
   ```bash
   docker images | grep aiagents
   ```

5. **查看系统资源**
   ```bash
   docker stats
   df -h
   free -h
   ```

### 联系支持

如果以上方法都无法解决问题：

1. 查看项目文档目录 `docs/`
2. 提交Issue到GitHub
3. 查看Docker官方文档

---

## ✅ 部署检查清单

部署前检查：
- [ ] Docker已安装（`docker --version`）
- [ ] Docker Compose已安装（`docker compose version`）
- [ ] 网络连接正常
- [ ] 端口8501未被占用
- [ ] 磁盘空间充足（至少5GB）

配置检查：
- [ ] 镜像源已配置（`docker info | grep Registry`）
- [ ] 必要目录已创建（data, log, config）
- [ ] 配置文件已准备（config.json）
- [ ] 环境变量已设置（.env）

部署后检查：
- [ ] 容器正常运行（`docker ps`）
- [ ] 日志无错误（`docker logs`）
- [ ] 网页可访问（http://localhost:8501）
- [ ] 功能正常使用

---

## 🎯 快速命令总结

```bash
# 完整部署流程（一键复制执行）
chmod +x *.sh && \
sudo ./fix-docker-mirror.sh && \
./start-docker.sh

# 日常运维
docker logs -f aiagents-stockinfo  # 查看日志
docker compose restart             # 重启服务
docker stats                       # 查看资源

# 故障排查
docker ps -a                       # 查看所有容器
docker logs aiagents-stockinfo     # 查看日志
docker exec -it aiagents-stockinfo bash  # 进入容器

# 清理重建
docker compose down && \
docker compose build --no-cache && \
docker compose up -d
```

---

**部署完成！** 🎉

现在你可以访问：http://localhost:8501 或 http://你的服务器IP:8501

祝使用愉快！ 📈🚀
