# 🚨 Docker镜像拉取错误快速修复

## 错误信息
```
ERROR [streamlit-app internal] load metadata for docker.io/library/python:3.11-slim
```

---

## ⚡ 快速解决（3步）

### 1️⃣ 赋予脚本执行权限
```bash
chmod +x fix-docker-mirror.sh start-docker.sh
```

### 2️⃣ 配置Docker镜像源
```bash
sudo ./fix-docker-mirror.sh
```

### 3️⃣ 重新启动
```bash
./start-docker.sh
```

**完成！** 🎉

---

## 📝 详细步骤

### 步骤1：配置Docker镜像源

```bash
# 自动配置（推荐）
sudo ./fix-docker-mirror.sh
```

这个脚本会：
- ✅ 自动备份原配置
- ✅ 配置国内镜像源
- ✅ 重启Docker服务
- ✅ 验证配置

### 步骤2：验证配置

```bash
# 查看Docker信息
docker info | grep -A 5 "Registry Mirrors"

# 测试拉取镜像
docker pull python:3.11-slim
```

如果能成功拉取镜像，说明配置成功！

### 步骤3：构建并启动

```bash
# 使用启动脚本
./start-docker.sh

# 或手动执行
docker compose build
docker compose up -d
```

---

## 🛠️ 手动配置（如果自动脚本失败）

### 1. 编辑Docker配置文件
```bash
sudo nano /etc/docker/daemon.json
```

### 2. 添加以下内容
```json
{
  "registry-mirrors": [
    "https://docker.mirrors.ustc.edu.cn",
    "https://hub-mirror.c.163.com",
    "https://mirror.baidubce.com"
  ]
}
```

### 3. 保存并重启Docker
```bash
# 保存文件：Ctrl+O，回车，Ctrl+X退出

# 重启Docker
sudo systemctl daemon-reload
sudo systemctl restart docker

# 验证Docker状态
sudo systemctl status docker
```

---

## 🔍 故障排查

### 问题1：脚本没有执行权限
```bash
chmod +x *.sh
```

### 问题2：Docker服务重启失败
```bash
# 查看错误日志
sudo journalctl -xeu docker

# 检查配置文件语法
cat /etc/docker/daemon.json | python3 -m json.tool
```

### 问题3：仍然无法拉取镜像
```bash
# 尝试不同的镜像源
# 编辑 /etc/docker/daemon.json，尝试只保留一个镜像源
# 例如只使用中科大镜像：
{
  "registry-mirrors": ["https://docker.mirrors.ustc.edu.cn"]
}

# 重启Docker
sudo systemctl restart docker
```

### 问题4：网络问题
```bash
# 测试网络连通性
ping docker.mirrors.ustc.edu.cn
curl -I https://docker.mirrors.ustc.edu.cn

# 如果无法连接，检查防火墙
sudo ufw status
```

---

## 📚 相关文档

- 详细说明：[Docker镜像源配置说明.md](Docker镜像源配置说明.md)
- Docker部署：[DOCKER_QUICK_START.md](DOCKER_QUICK_START.md)
- 使用说明：[Docker使用说明.md](Docker使用说明.md)

---

## 🆘 还是不行？

### 最后的解决方案

如果上述方法都不行，可以尝试：

#### 方案A：使用阿里云镜像加速器

1. 注册阿里云账号
2. 访问：https://cr.console.aliyun.com/cn-hangzhou/instances/mirrors
3. 获取你的专属加速地址
4. 配置到 `/etc/docker/daemon.json`

#### 方案B：使用代理

如果有HTTP代理：

```bash
# 创建配置文件
sudo mkdir -p /etc/systemd/system/docker.service.d
sudo nano /etc/systemd/system/docker.service.d/http-proxy.conf

# 添加内容：
[Service]
Environment="HTTP_PROXY=http://proxy-server:port"
Environment="HTTPS_PROXY=http://proxy-server:port"

# 重启Docker
sudo systemctl daemon-reload
sudo systemctl restart docker
```

#### 方案C：离线安装

1. 在有网络的机器上构建镜像
2. 导出镜像：
   ```bash
   docker save aiagents-stockinfo:latest -o aiagents-stockinfo.tar
   ```
3. 传输到目标服务器
4. 导入镜像：
   ```bash
   docker load -i aiagents-stockinfo.tar
   ```
5. 直接运行容器

---

## ✅ 验证成功

配置成功后，你应该能看到：

```bash
$ docker pull python:3.11-slim
3.11-slim: Pulling from library/python
✓ Successfully pulled
```

然后就可以正常使用了！

```bash
./start-docker.sh
```

---

**祝你顺利！** 🚀

如有问题，请查看详细文档或提交Issue。
