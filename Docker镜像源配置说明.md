# 🔧 Docker镜像源配置说明

## 问题描述

如果遇到以下错误：
```
ERROR [streamlit-app internal] load metadata for docker.io/library/python:3.11-slim
```

这是因为Docker无法从官方源下载镜像，需要配置国内镜像源。

---

## 快速解决（推荐）

### 方法一：自动配置脚本 ⭐

```bash
# 赋予执行权限
chmod +x fix-docker-mirror.sh

# 执行配置脚本
sudo ./fix-docker-mirror.sh
```

脚本会自动：
1. 备份原配置
2. 配置镜像源
3. 重启Docker服务
4. 验证配置

### 方法二：手动配置

1. **创建/编辑Docker配置文件**
```bash
sudo mkdir -p /etc/docker
sudo nano /etc/docker/daemon.json
```

2. **添加以下内容**
```json
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
```

3. **重启Docker服务**
```bash
sudo systemctl daemon-reload
sudo systemctl restart docker
```

4. **验证配置**
```bash
docker info | grep -A 10 "Registry Mirrors"
```

---

## 配置完成后

重新构建镜像：
```bash
# 方法1：使用启动脚本
./start-docker.sh

# 方法2：使用Docker Compose
docker compose build
docker compose up -d

# 方法3：使用Docker命令
docker build -t aiagents-stockinfo .
```

---

## 可用的国内镜像源

| 镜像源 | 地址 | 说明 |
|--------|------|------|
| 中科大镜像 | https://docker.mirrors.ustc.edu.cn | 稳定，推荐 |
| 网易镜像 | https://hub-mirror.c.163.com | 速度快 |
| 百度镜像 | https://mirror.baidubce.com | 可靠 |
| DaoCloud镜像 | https://docker.m.daocloud.io | 备用 |
| 阿里云镜像 | https://your-id.mirror.aliyuncs.com | 需要注册获取ID |

---

## 阿里云镜像源（可选）

如果上述镜像源速度不理想，可以使用阿里云镜像加速器：

1. **注册阿里云账号**
   访问：https://cr.console.aliyun.com/cn-hangzhou/instances/mirrors

2. **获取专属加速地址**
   格式：`https://your-id.mirror.aliyuncs.com`

3. **添加到配置文件**
```json
{
  "registry-mirrors": [
    "https://your-id.mirror.aliyuncs.com",
    "https://docker.mirrors.ustc.edu.cn"
  ]
}
```

---

## 常见问题

### 1. 配置后仍然无法拉取镜像

**原因**：可能是网络问题或镜像源失效

**解决方案**：
```bash
# 测试镜像源连通性
curl -I https://docker.mirrors.ustc.edu.cn

# 尝试手动拉取镜像
docker pull python:3.11-slim

# 如果失败，尝试更换镜像源
```

### 2. Docker重启失败

**查看错误日志**：
```bash
sudo journalctl -xeu docker
```

**检查配置文件语法**：
```bash
cat /etc/docker/daemon.json | python3 -m json.tool
```

### 3. 权限问题

**确保有sudo权限**：
```bash
sudo systemctl status docker
```

### 4. 防火墙问题

**临时关闭防火墙测试**：
```bash
sudo ufw disable
# 测试完成后记得重新开启
sudo ufw enable
```

---

## 验证配置成功

配置成功后，执行以下命令应该能看到配置的镜像源：

```bash
docker info
```

输出应包含：
```
Registry Mirrors:
  https://docker.mirrors.ustc.edu.cn/
  https://hub-mirror.c.163.com/
  ...
```

---

## 其他优化建议

### 1. 配置Docker存储驱动

如果磁盘空间紧张，可以配置存储驱动：

```json
{
  "registry-mirrors": [...],
  "storage-driver": "overlay2",
  "storage-opts": [
    "overlay2.override_kernel_check=true"
  ]
}
```

### 2. 配置日志限制

防止日志文件过大：

```json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "50m",
    "max-file": "3"
  }
}
```

### 3. 配置代理（如果使用代理服务器）

创建 `/etc/systemd/system/docker.service.d/http-proxy.conf`：

```ini
[Service]
Environment="HTTP_PROXY=http://proxy.example.com:8080"
Environment="HTTPS_PROXY=http://proxy.example.com:8080"
Environment="NO_PROXY=localhost,127.0.0.1"
```

---

## 完整配置示例

`/etc/docker/daemon.json` 完整配置：

```json
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
  },
  "storage-driver": "overlay2",
  "storage-opts": [
    "overlay2.override_kernel_check=true"
  ],
  "live-restore": true,
  "userland-proxy": false,
  "experimental": false,
  "metrics-addr": "127.0.0.1:9323",
  "max-concurrent-downloads": 10,
  "max-concurrent-uploads": 5,
  "default-ulimits": {
    "nofile": {
      "Name": "nofile",
      "Hard": 64000,
      "Soft": 64000
    }
  }
}
```

---

## 测试镜像拉取

配置完成后测试：

```bash
# 拉取Python镜像
docker pull python:3.11-slim

# 拉取其他常用镜像
docker pull nginx:alpine
docker pull redis:alpine
```

如果能成功拉取，说明配置正确！

---

## 快速命令参考

```bash
# 配置镜像源（自动）
sudo ./fix-docker-mirror.sh

# 重启Docker
sudo systemctl restart docker

# 查看Docker信息
docker info

# 测试拉取镜像
docker pull python:3.11-slim

# 查看Docker日志
sudo journalctl -xeu docker
```

---

**配置完成后，重新执行 `./start-docker.sh` 即可！** 🚀
