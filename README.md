# Whatalert 监控告警系统

<div align="center">

一个功能强大的多租户监控告警系统，支持分布式部署，兼容 Prometheus 查询语法。

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![Vue](https://img.shields.io/badge/Vue-3.x-brightgreen.svg)](https://vuejs.org/)
[![Docker](https://img.shields.io/badge/Docker-ready-blue.svg)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

</div>

---

## ✨ 核心特性

### 🎯 告警管理
- **灵活的告警规则** - 支持 PromQL 查询语法
- **智能分组** - 类似 Alertmanager 的告警聚合
- **可配置重发** - 每个规则独立配置重复发送间隔（15分钟～6小时）
- **模板变量渲染** - 支持 `{{ $labels.xxx }}`、`{{ $value }}` 等动态变量
- **告警静默** - 灵活的静默规则配置
- **多级路由** - 支持复杂的告警路由策略

### 🔔 通知渠道
- **多渠道支持** - 飞书、钉钉、企业微信、邮件、自定义Webhook
- **批量通知** - 支持告警合并发送，减少通知噪音
- **通知模板** - 自定义通知内容和格式
- **通知过滤** - 基于标签的智能过滤
- **富文本卡片** - 飞书/钉钉高级消息卡片

### 🏢 多租户架构
- **租户隔离** - 完整的多租户数据隔离
- **项目管理** - 支持项目级别的资源隔离
- **RBAC权限** - 细粒度的角色权限控制（Owner/Admin/Member/Viewer）
- **独立配置** - 每个租户/项目独立的告警策略

### 🚀 分布式部署
- **Redis 支持** - 分布式锁和告警分组
- **水平扩展** - 支持多实例部署
- **高可用** - 自动故障转移
- **负载均衡** - 支持 Kubernetes HPA

### 📊 监控数据源
- **Prometheus** - 原生支持
- **VictoriaMetrics** - 完美兼容
- **多数据源** - 支持配置多个数据源
- **连接测试** - 创建数据源时自动验证连接

---

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────┐
│                     Web 界面 (Vue 3)                      │
│           Element Plus + Vite + Pinia                    │
└─────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│              API 服务 (FastAPI)                          │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │ 规则评估器   │  │ 告警分组器    │  │ 通知服务      │  │
│  │  调度执行    │  │  智能聚合     │  │  多渠道发送   │  │
│  └─────────────┘  └──────────────┘  └───────────────┘  │
└─────────────────────────────────────────────────────────┘
           │                    │                │
           ▼                    ▼                ▼
    ┌───────────┐        ┌──────────┐    ┌──────────────┐
    │Prometheus │        │  Redis   │    │ 飞书/钉钉/邮件│
    │ VM        │        │ 分布式锁  │    │    Webhook   │
    └───────────┘        │ 告警分组  │    └──────────────┘
                         └──────────┘
                              │
                              ▼
                        ┌──────────┐
                        │  MySQL   │
                        │ 数据持久化│
                        └──────────┘
```

---

## 📦 快速部署

### Docker Compose（推荐用于测试）

```bash
# 1. 克隆代码
git clone https://github.com/ZYWNB666/Whatalert.git
cd Whatalert

# 2. 配置数据库和Redis
cp config/config.example.yaml config/config.yaml
vim config/config.yaml  # 修改数据库和Redis配置

# 3. 初始化数据库
mysql -u root -p < scripts/init_database.sql

# 4. 启动服务
docker-compose up -d

# 5. 访问系统
open http://localhost
```

**默认账号**:
- 用户名: `admin`
- 密码: `admin123`

### Kubernetes 部署

详细部署步骤请查看：**[Docker & Kubernetes 部署指南](DOCKER_DEPLOYMENT.md)**

```bash
# 创建命名空间
kubectl create namespace whatalert

# 创建密钥
kubectl create secret generic whatalert-secret \
  --from-literal=mysql-root-password='YourPassword' \
  --from-literal=redis-password='YourRedisPassword' \
  --from-literal=jwt-secret='YourJWTSecret' \
  -n whatalert

# 部署应用
kubectl apply -f k8s/
```

---

## 📁 项目结构

```
Whatalert/
├── app/                      # 后端应用
│   ├── api/                  # API 路由
│   │   ├── alert_rules.py    # 告警规则API
│   │   ├── notifications.py  # 通知渠道API
│   │   ├── auth.py           # 认证API
│   │   └── ...
│   ├── core/                 # 核心功能
│   │   ├── config.py         # 配置加载
│   │   ├── security.py       # 安全认证
│   │   ├── permissions.py    # 权限检查
│   │   └── distributed_lock.py # 分布式锁
│   ├── db/                   # 数据库
│   │   ├── database.py       # 数据库连接
│   │   └── redis_client.py   # Redis连接
│   ├── models/               # 数据模型
│   ├── schemas/              # Pydantic Schemas
│   ├── services/             # 业务服务
│   │   ├── alert_manager.py  # 告警管理
│   │   ├── evaluator.py      # 规则评估
│   │   ├── notifier.py       # 通知发送
│   │   └── alert_grouper.py  # 告警分组
│   ├── middleware/           # 中间件
│   │   └── audit.py          # 审计日志
│   └── main.py               # 应用入口
├── web/                      # 前端应用（Vue 3）
│   ├── src/
│   │   ├── views/            # 页面组件
│   │   ├── api/              # API请求
│   │   ├── stores/           # Pinia状态
│   │   └── router/           # 路由配置
│   └── dist/                 # 构建产物
├── config/                   # 配置文件
│   ├── config.yaml           # 主配置
│   └── config.example.yaml   # 配置示例
├── scripts/                  # 数据库脚本
│   ├── init_database.sql     # 完整初始化脚本（包含18张表+初始数据）
│   └── check_repeat_interval.py # 数据检查脚本
├── docs/                     # 文档
│   ├── ARCHITECTURE.md       # 架构设计
│   ├── FEATURES.md           # 功能列表
│   ├── USAGE.md              # 使用指南
│   ├── PERMISSIONS.md        # 权限说明
│   ├── labels_annotations_guide.md # 标签注释指南
│   └── ...
├── Dockerfile                # 后端镜像
├── docker-compose.yml        # Compose配置
├── requirements.txt          # Python依赖
└── README.md                 # 项目说明
```

---

## 🔧 配置说明

### config.yaml

```yaml
# MySQL 数据库配置
database:
  host: "mysql"
  port: 3306
  username: "root"
  password: "your-password"
  database: "whatalert"

# Redis 配置（分布式部署必需）
redis:
  host: "redis"
  port: 6379
  password: "your-password"
  db: 0

# 日志配置
logging:
  level: "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
```

### 告警规则配置

```yaml
# 示例：监控Pod内存使用率
name: "Pod内存告警"
expr: 'container_memory_usage_bytes / container_spec_memory_limit_bytes * 100 > 80'
eval_interval: 60          # 评估间隔（秒）
for_duration: 300          # 持续时间（秒）
repeat_interval: 1800      # 重复发送间隔（秒，30分钟）
severity: "warning"
labels:
  team: "backend"
  service: "api"
annotations:
  summary: "Pod {{ $labels.pod }} 内存使用率过高"
  description: "实例 {{$labels.instance}} 的Pod {{ $labels.pod }} 内存使用率为 {{ $value }}%"
```

---

## 📚 文档

- **[架构设计](docs/ARCHITECTURE.md)** - 系统架构和设计理念
- **[功能列表](docs/FEATURES.md)** - 完整功能清单
- **[API使用指南](docs/USAGE.md)** - API接口说明
- **[权限说明](docs/PERMISSIONS.md)** - RBAC权限体系
- **[告警分组指南](docs/alert_grouping_guide.md)** - 告警分组配置
- **[标签注释指南](docs/labels_annotations_guide.md)** - 标签和注释使用
- **[Redis集成](docs/redis_integration.md)** - Redis功能说明
- **[部署指南](DOCKER_DEPLOYMENT.md)** - Docker & K8s部署

---

## 🛠️ 数据库管理

### 初始化数据库

```bash
# 首次部署时执行
mysql -u root -p whatalert < scripts/init_database.sql
```

**说明**：
- `init_database.sql` 包含完整的数据库结构（18张表）
- 包含默认租户、项目、角色、权限和管理员账号
- 默认管理员账号：`admin` / 密码：`admin123`
- ⚠️ 首次登录后请立即修改密码

### 在容器中操作

```bash
# Docker Compose
docker exec -it alert-mysql mysql -uroot -p

# Kubernetes
kubectl exec -it statefulset/mysql -n whatalert -- mysql -uroot -p
```

### 数据库备份与恢复

```bash
# 备份数据库
mysqldump -u root -p whatalert > whatalert_backup_$(date +%Y%m%d).sql

# 恢复数据库
mysql -u root -p whatalert < whatalert_backup_20250117.sql
```

---

## 🎨 主要功能

### 1. 仪表板
- 实时统计当前告警、历史告警、活跃规则
- 最近告警时间线
- 按等级分类的告警分布

### 2. 告警规则
- 创建/编辑告警规则
- PromQL表达式测试
- 标签和注释配置（键值对表单）
- 通知渠道选择
- 规则启用/禁用
- 重复发送间隔配置（15分钟/30分钟/1小时/3小时/6小时）

### 3. 当前告警
- 按规则分组展示
- 卡片式列表，点击查看详情
- 分页显示（10/20/50条可选）
- 显示告警状态、等级、触发时间

### 4. 历史告警
- 按规则分组展示已恢复的告警
- 显示持续时间
- 支持搜索和过滤

### 5. 通知渠道
- 飞书、钉钉、企业微信、邮件、Webhook
- 通知测试功能
- 标签过滤配置
- 启用/禁用控制

### 6. 告警静默
- 时间范围静默
- 标签匹配静默
- 支持注释说明

### 7. 数据源管理
- Prometheus/VictoriaMetrics
- 连接测试
- 多数据源支持

### 8. 用户与权限
- 租户管理
- 项目管理
- 角色权限（Owner/Admin/Member/Viewer）
- 审计日志

---

## 🔒 安全特性

- **JWT认证** - 基于Token的安全认证，支持刷新令牌
- **RBAC权限** - 细粒度的角色权限控制
- **租户隔离** - 完整的数据隔离，确保数据安全
- **项目隔离** - 项目级别的资源隔离
- **审计日志** - 记录所有增删改操作
- **密码加密** - BCrypt加密存储
- **会话管理** - 分布式会话支持

---

## 📊 技术栈

### 后端
- **FastAPI** - 现代Python Web框架
- **SQLAlchemy** - 异步ORM框架
- **MySQL** - 关系型数据库
- **Redis** - 缓存和分布式锁
- **Loguru** - 日志框架
- **APScheduler** - 定时任务调度
- **httpx** - 异步HTTP客户端

### 前端
- **Vue 3** - 渐进式JavaScript框架
- **Element Plus** - UI组件库
- **Vite** - 下一代构建工具
- **Pinia** - 状态管理
- **Vue Router** - 路由管理
- **Axios** - HTTP请求库

---

## 🚀 开发指南

### 后端开发

```bash
# 安装依赖
pip install -r requirements.txt

# 启动开发服务器
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# API文档
open http://localhost:8000/docs
```

### 前端开发

```bash
cd web

# 安装依赖
npm install

# 启动开发服务器
npm run dev

# 构建生产版本
npm run build
```

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

### 贡献指南
1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

---

## 📄 许可证

MIT License

---

## 📞 联系方式

- **GitHub**: [ZYWNB666/Whatalert](https://github.com/ZYWNB666/Whatalert)
- **Issues**: [提交问题](https://github.com/ZYWNB666/Whatalert/issues)

---

<div align="center">

**⭐ 如果这个项目对你有帮助，请给个 Star！**

Made with ❤️ by ZYWNB666

</div>
