# 🐳 Docker快速使用说明

## 一、准备工作

### 1. 安装Docker（Ubuntu/Debian）
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
newgrp docker
```

### 2. 安装Docker Compose
```bash
sudo apt-get install docker-compose-plugin
```

## 二、快速启动（三种方法）

### 方法一：一键启动脚本 ⭐️推荐
```bash
# 赋予执行权限
chmod +x start-docker.sh

# 启动服务
./start-docker.sh
```

### 方法二：Docker Compose
```bash
# 构建并启动
docker compose up -d

# 或者使用旧版命令
docker-compose up -d
```

### 方法三：Docker命令
```bash
# 构建镜像
docker build -t aiagents-stockinfo .

# 运行容器
docker run -d \
  -p 8501:8501 \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/log:/app/log \
  -v $(pwd)/config:/app/config \
  --name aiagents-stockinfo \
  aiagents-stockinfo
```

## 三、访问应用

启动成功后访问：
- 本地：http://localhost:8501
- 远程：http://你的服务器IP:8501

## 四、常用命令

```bash
# 查看运行状态
docker ps

# 查看日志
docker logs -f aiagents-stockinfo

# 停止服务
./stop-docker.sh
# 或
docker compose down

# 重启服务
docker compose restart

# 进入容器
docker exec -it aiagents-stockinfo bash
```

## 五、故障排查

### 1. 查看日志
```bash
docker logs -f aiagents-stockinfo
```

### 2. 端口被占用
```bash
# 查看端口占用
sudo lsof -i :8501

# 或修改docker-compose.yml中的端口
ports:
  - "8080:8501"  # 改为8080端口
```

### 3. 无法访问
```bash
# 开放防火墙端口
sudo ufw allow 8501
```

### 4. 重新构建（清除缓存）
```bash
docker compose down
docker compose build --no-cache
docker compose up -d
```

## 六、数据持久化

以下目录会自动保存到宿主机：
- `./data` - 数据文件
- `./log` - 日志文件
- `./config` - 配置文件

即使删除容器，这些数据也不会丢失。

## 七、更新应用

```bash
# 1. 拉取最新代码
git pull

# 2. 停止旧容器
docker compose down

# 3. 重新构建
docker compose build --no-cache

# 4. 启动新容器
docker compose up -d
```

## 八、完全清理

如果需要完全删除所有数据和容器：
```bash
# 停止并删除容器
docker compose down

# 删除镜像
docker rmi aiagents-stockinfo

# 删除数据（谨慎操作！）
rm -rf data/ log/
```

---

## 快速参考命令

| 操作 | 命令 |
|------|------|
| 启动 | `./start-docker.sh` 或 `docker compose up -d` |
| 停止 | `./stop-docker.sh` 或 `docker compose down` |
| 重启 | `docker compose restart` |
| 查看日志 | `docker logs -f aiagents-stockinfo` |
| 查看状态 | `docker ps` |
| 进入容器 | `docker exec -it aiagents-stockinfo bash` |

---

**需要详细说明？** 查看 [DOCKER_QUICK_START.md](DOCKER_QUICK_START.md)
