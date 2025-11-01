# VPNGate 自动轮换工具

[![Python Version](https://img.shields.io/badge/python-3.6+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

一个基于 VPNGate 公共 VPN 服务的自动节点获取和轮换工具。自动从 VPNGate 获取高质量节点，并每 10 分钟自动切换 VPN 出口 IP，适用于需要频繁更换 IP 地址的场景。

## ✨ 特性

- 🔄 **自动节点更新**：每 24 小时从 VPNGate API 自动获取最新的高质量节点
- 🎯 **智能筛选**：仅保留评分 > 1,000,000 的高质量节点
- 🔁 **自动轮换**：每 10 分钟自动切换到新的 VPN 节点
- 🛡️ **安全模式**：不修改全局路由，仅创建 VPN 隧道接口
- ✅ **连接验证**：自动验证 VPN 连接是否成功，失败则切换下一个节点
- 📊 **详细日志**：记录所有操作日志，方便排查问题
- 🌍 **全球节点**：支持来自世界各地的 VPNGate 公共节点

## 📋 系统要求

### 操作系统
- Linux（推荐 Ubuntu 20.04+, Debian 10+, CentOS 7+）

### 依赖软件
- Python 3.6+
- OpenVPN 客户端
- curl
- iproute2 工具包

### Python 依赖
- requests

## 🚀 安装指南

### 1. 安装系统依赖

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install -y python3 python3-pip openvpn curl iproute2
```

**CentOS/RHEL:**
```bash
sudo yum install -y python3 python3-pip openvpn curl iproute2
```

### 2. 安装 Python 依赖

```bash
pip3 install requests
```

### 3. 下载项目文件

```bash
# 克隆或下载本项目
git clone <repository-url>
cd <project-directory>

# 添加执行权限
chmod +x fetch_vpngate.py switch_vpngate_autorotate.py
```

### 4. 创建必要的目录

```bash
# 确保日志目录存在
sudo mkdir -p /var/log
sudo mkdir -p /opt
sudo mkdir -p /var/run

# 设置权限（如果需要非 root 用户运行）
sudo chown $USER:$USER /var/log /opt /var/run
```

## 📖 使用方法

### 方式一：分步运行（推荐用于测试）

#### 步骤 1：获取节点池

首先运行节点获取脚本，从 VPNGate 下载高质量节点列表：

```bash
sudo python3 fetch_vpngate.py
```

这个脚本会：
- 连接到 VPNGate API
- 筛选出评分 > 1,000,000 的节点
- 保存到 `/opt/vpngate_pool.csv`
- 每 24 小时自动更新一次

#### 步骤 2：启动自动轮换

然后运行 VPN 自动切换脚本：

```bash
sudo python3 switch_vpngate_autorotate.py
```

这个脚本会：
- 从节点池中随机选择节点
- 连接并验证 VPN 是否工作
- 每 10 分钟自动切换到新节点
- 失败时自动尝试下一个节点

### 方式二：使用 systemd 服务（推荐用于生产环境）

创建 systemd 服务文件以实现开机自启和后台运行。

#### 创建节点获取服务

```bash
sudo tee /etc/systemd/system/vpngate-fetch.service > /dev/null <<EOF
[Unit]
Description=VPNGate Node Pool Fetcher
After=network.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 $(pwd)/fetch_vpngate.py
Restart=always
RestartSec=60

[Install]
WantedBy=multi-user.target
EOF
```

#### 创建自动轮换服务

```bash
sudo tee /etc/systemd/system/vpngate-rotate.service > /dev/null <<EOF
[Unit]
Description=VPNGate Auto Rotate Service
After=network.target vpngate-fetch.service
Requires=vpngate-fetch.service

[Service]
Type=simple
ExecStart=/usr/bin/python3 $(pwd)/switch_vpngate_autorotate.py
Restart=always
RestartSec=30

[Install]
WantedBy=multi-user.target
EOF
```

#### 启动服务

```bash
# 重新加载 systemd
sudo systemctl daemon-reload

# 启动服务
sudo systemctl start vpngate-fetch
sudo systemctl start vpngate-rotate

# 设置开机自启
sudo systemctl enable vpngate-fetch
sudo systemctl enable vpngate-rotate

# 查看服务状态
sudo systemctl status vpngate-fetch
sudo systemctl status vpngate-rotate
```

## ⚙️ 配置说明

### fetch_vpngate.py 配置参数

在脚本开头修改以下参数：

```python
API_URL = "http://www.vpngate.net/api/iphone/"  # VPNGate API 地址
POOL_FILE = "/opt/vpngate_pool.csv"              # 节点池保存路径
MIN_SCORE = 1000000                              # 最低节点分数（越高质量越好）
INTERVAL = 86400                                 # 更新间隔（秒），默认 24 小时
```

### switch_vpngate_autorotate.py 配置参数

在脚本开头修改以下参数：

```python
POOL_FILE = "/opt/vpngate_pool.csv"              # 节点池文件路径
LOG_FILE = "/var/log/vpngate_autorotate.log"    # 主日志文件
OVPN_FILE = "/opt/vpngate_current.ovpn"          # 当前 OpenVPN 配置文件
OVPN_LOG_FILE = "/var/log/openvpn_client.log"   # OpenVPN 日志
PID_FILE = "/var/run/vpngate_switch.pid"        # 进程 PID 文件

ROTATE_INTERVAL = 600                            # 轮换间隔（秒），默认 10 分钟
WAIT_LOG_READY = 10                             # 等待日志就绪时间（秒）
MAX_VERIFY_TRIES = 5                            # 最大验证尝试次数
```

## 📊 日志查看

### 实时查看轮换日志

```bash
tail -f /var/log/vpngate_autorotate.log
```

### 查看 OpenVPN 连接日志

```bash
tail -f /var/log/openvpn_client.log
```

### 使用 systemd 查看日志

```bash
# 查看节点获取日志
sudo journalctl -u vpngate-fetch -f

# 查看自动轮换日志
sudo journalctl -u vpngate-rotate -f
```

## 🔍 工作原理

### 节点获取流程
1. 从 VPNGate API 获取所有公开节点列表
2. 解析 CSV 格式的节点数据
3. 筛选评分 > 1,000,000 的高质量节点
4. 保存到本地节点池文件
5. 每 24 小时重复一次

### VPN 轮换流程
1. 从节点池随机选择一个节点
2. 停止旧的 OpenVPN 连接（如果存在）
3. 解码 Base64 格式的 OpenVPN 配置
4. 添加安全配置（不修改全局路由）
5. 启动 OpenVPN 连接
6. 通过 tun 接口验证连接是否成功
7. 检查出口 IP 是否已改变
8. 等待 10 分钟后切换到下一个节点

### 安全模式说明
脚本使用安全模式运行，不会修改系统的全局路由表。这意味着：
- ✅ 只创建 VPN 隧道接口（tun0/tun1等）
- ✅ 不影响系统的正常网络访问
- ✅ 需要手动指定应用通过 VPN 接口访问
- ⚠️ 如需应用使用 VPN，需配置应用通过 tun 接口路由

### 如何让应用使用 VPN

使用 `curl` 通过 VPN 访问：
```bash
# 假设 VPN 接口为 tun0
curl --interface tun0 https://ipinfo.io/json
```

使用 `ip route` 为特定 IP 段添加路由：
```bash
# 将特定网段的流量路由到 VPN
sudo ip route add 1.2.3.0/24 dev tun0
```

## 🛠️ 故障排查

### 问题：无法获取节点池

**症状：** `fetch_vpngate.py` 报错无法连接到 API

**解决方案：**
1. 检查网络连接：`ping www.vpngate.net`
2. 检查防火墙设置
3. 尝试使用代理访问
4. 手动访问 http://www.vpngate.net/api/iphone/ 确认 API 可用

### 问题：VPN 连接失败

**症状：** 日志显示 "❌ 验证失败"

**解决方案：**
1. 检查 OpenVPN 是否正确安装：`which openvpn`
2. 查看 OpenVPN 详细日志：`cat /var/log/openvpn_client.log`
3. 确认防火墙允许 UDP 端口（通常是 1194）
4. 尝试增加 `WAIT_LOG_READY` 时间
5. 降低 `MIN_SCORE` 阈值以获取更多节点

### 问题：服务频繁重启

**症状：** systemd 日志显示服务不断重启

**解决方案：**
1. 确保节点池文件存在：`ls -l /opt/vpngate_pool.csv`
2. 先手动运行 `fetch_vpngate.py` 生成节点池
3. 检查 Python 依赖是否安装：`pip3 list | grep requests`
4. 查看详细错误日志：`journalctl -u vpngate-rotate -n 50`

### 问题：无法检测到 tun 接口

**症状：** 日志显示无法找到 tun 接口

**解决方案：**
1. 检查 tun 模块是否加载：`lsmod | grep tun`
2. 手动加载 tun 模块：`sudo modprobe tun`
3. 确保内核支持 tun/tap：`ls -l /dev/net/tun`

### 问题：权限错误

**症状：** 无法写入日志或配置文件

**解决方案：**
```bash
# 使用 root 权限运行
sudo python3 switch_vpngate_autorotate.py

# 或者修改文件权限
sudo chown -R $USER:$USER /opt /var/log /var/run
```

## ⚠️ 注意事项

1. **法律合规性**：使用 VPN 时请遵守当地法律法规，VPNGate 在某些地区可能受到限制
2. **安全性**：VPNGate 是公共免费 VPN 服务，不建议用于传输敏感数据
3. **隐私**：公共 VPN 节点可能记录流量，请勿用于需要高度隐私保护的场景
4. **性能**：免费节点性能不稳定，速度和延迟可能较差
5. **可用性**：节点可能随时下线，脚本会自动尝试下一个节点
6. **资源占用**：频繁切换节点会产生一定的 CPU 和内存开销

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

### 开发路线图
- [ ] 支持配置文件而不是硬编码参数
- [ ] 添加 Web 界面监控节点状态
- [ ] 支持多个 VPN 协议（如 WireGuard）
- [ ] 添加节点性能测试和排序
- [ ] 支持黑名单功能（排除特定国家/IP）
- [ ] 增加 Docker 部署支持

## 📄 许可证

本项目采用 MIT 许可证。详见 [LICENSE](LICENSE) 文件。

## 🙏 致谢

- [VPNGate](https://www.vpngate.net/) - 提供免费的公共 VPN 服务
- 所有贡献者和用户

## 📞 联系方式

如有问题或建议，请通过以下方式联系：
- 提交 [Issue](https://github.com/your-repo/issues)
- 发送邮件至：your-email@example.com

---

**免责声明**：本工具仅供学习和研究使用。使用本工具产生的任何后果由使用者自行承担，开发者不承担任何责任。
