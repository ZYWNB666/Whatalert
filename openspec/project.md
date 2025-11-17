# Project Context

## Purpose
Whatalert 是一个功能强大的多租户监控告警系统，支持分布式部署，兼容 Prometheus 查询语法。系统提供灵活的告警规则配置、智能告警分组、多渠道通知、告警静默管理等核心功能，适用于企业级监控场景。

## Tech Stack

### Backend
- **Python 3.11+** - 主要编程语言
- **FastAPI 0.104+** - 现代异步 Web 框架
- **SQLAlchemy 2.0+** - ORM 框架（支持异步）
- **MySQL** - 主数据库
- **Redis 5.0+** - 缓存、分布式锁、会话管理
- **Loguru** - 日志框架
- **APScheduler** - 定时任务调度
- **Pydantic** - 数据验证

### Frontend
- **Vue 3** - 前端框架
- **Element Plus** - UI 组件库
- **Vite** - 构建工具
- **Pinia** - 状态管理
- **Vue Router** - 路由管理

### Infrastructure
- **Docker** - 容器化
- **Docker Compose** - 本地开发环境
- **Kubernetes** - 生产环境部署
- **Nginx** - 前端静态资源服务
- **Prometheus/VictoriaMetrics** - 监控数据源

### External Services
- **飞书 (Feishu)** - 告警通知渠道
- **钉钉 (DingTalk)** - 告警通知渠道
- **企业微信 (WeChat Work)** - 告警通知渠道
- **SMTP** - 邮件通知

## Project Conventions

### Code Style

#### Python Backend
- **格式化**: 使用 Black (默认配置)
- **Linting**: Flake8
- **类型检查**: MyPy
- **命名规范**:
  - 文件/模块: `snake_case` (如 `alert_manager.py`)
  - 类名: `PascalCase` (如 `AlertManager`, `AlertRule`)
  - 函数/变量: `snake_case` (如 `evaluate_rule`, `alert_event`)
  - 常量: `UPPER_SNAKE_CASE` (如 `MAX_RETRY_COUNT`)
  - 私有成员: 前缀 `_` (如 `_internal_state`)
- **导入顺序**: 标准库 → 第三方库 → 本地模块
- **文档字符串**: 使用中文注释，简洁明了

#### Vue Frontend
- **风格指南**: Vue 3 官方风格指南
- **组件命名**: PascalCase 文件名 (如 `AlertRules.vue`)
- **变量命名**: camelCase
- **CSS**: 使用 scoped 样式

### Architecture Patterns

#### 后端架构
- **三层架构**:
  - API Layer (`app/api/`): 路由和请求处理
  - Service Layer (`app/services/`): 业务逻辑
  - Data Layer (`app/models/`, `app/db/`): 数据访问
- **依赖注入**: 使用 FastAPI 的依赖注入系统
- **异步优先**: 所有 I/O 操作使用 async/await
- **多租户**: 所有数据查询必须包含 tenant_id 过滤
- **RBAC**: 基于资源和动作的权限控制 (`resource:action` 格式)

#### 核心模块设计
- **AlertEvaluationScheduler**: 定时评估告警规则
- **AlertManager**: 管理告警生命周期和状态
- **AlertGrouper**: 告警分组和批量发送（支持 Redis 和内存两种实现）
- **Notifier**: 多渠道通知发送

#### 数据库设计
- 所有表必须包含 `tenant_id` 字段
- 使用 `created_at` 和 `updated_at` 时间戳
- 软删除使用 `is_deleted` 字段
- 关键查询字段添加索引（特别是 `(tenant_id, *)` 组合索引）

### Testing Strategy
- **框架**: pytest + pytest-asyncio
- **覆盖率**: pytest-cov
- **测试类型**:
  - 单元测试: 核心业务逻辑
  - 集成测试: API 端点
  - 异步测试: 使用 `@pytest.mark.asyncio`
- **测试数据**: 使用 fixture 创建隔离的测试环境
- **命名**: `test_<功能>_<场景>.py`

### Git Workflow
- **分支策略**:
  - `main`: 生产环境分支
  - `develop`: 开发分支
  - `feature/*`: 功能分支
  - `fix/*`: 修复分支
  - `hotfix/*`: 紧急修复
- **提交信息**: 简洁的中文描述，清晰表达变更内容
- **Pull Request**: 必须通过 review 才能合并

## Domain Context

### 监控告警术语
- **AlertRule (告警规则)**: 定义告警条件和评估逻辑
- **PromQL**: Prometheus 查询语言，用于查询时序数据
- **Datasource (数据源)**: Prometheus 或 VictoriaMetrics 实例
- **AlertEvent (告警事件)**: 当前触发的告警
- **Fingerprint (指纹)**: 告警的唯一标识，基于规则 ID 和标签生成
- **Silence (静默)**: 临时屏蔽告警通知
- **Grouping (分组)**: 将相似告警合并后批量发送
- **Severity (严重级别)**: critical, warning, info
- **Status (状态)**: pending, firing, resolved

### 告警生命周期
1. **pending**: 条件满足但未达到持续时间
2. **firing**: 条件持续满足，开始发送通知
3. **resolved**: 条件不再满足，告警恢复

### 通知渠道配置
- **filter_config**: 支持 `include_labels` 和 `exclude_labels` 进行标签过滤
- **高级配置**: 飞书支持 JSON 卡片格式，钉钉支持签名认证

## Important Constraints

### 技术约束
- Python 版本必须 >= 3.11（使用现代异步特性）
- MySQL 必须支持 JSON 字段类型
- Redis 必须 >= 5.0（原生异步支持）
- 所有数据库查询必须是异步的（使用 aiomysql）

### 业务约束
- 多租户数据严格隔离，不允许跨租户访问
- 告警评估间隔不小于 10 秒（避免频繁查询数据源）
- 通知频率受 `repeat_interval` 控制，避免告警风暴
- 默认管理员账号: `admin/admin123`

### 性能约束
- 单个租户告警规则数量建议 < 1000
- 告警分组批次大小建议 < 100
- 数据库连接池大小根据实例数量调整
- Redis 用于分布式锁，超时时间默认 30 秒

### 安全约束
- 密码必须使用 bcrypt 加密
- JWT Token 有效期默认 7 天
- 所有 API 操作记录审计日志
- 敏感配置（如数据源密码）加密存储

## External Dependencies

### 监控数据源
- **Prometheus**: 标准 HTTP API (`/api/v1/query`)
- **VictoriaMetrics**: 兼容 Prometheus API

### 通知服务
- **飞书开放平台**: Webhook URL 或机器人
- **钉钉开放平台**: Webhook + 签名认证
- **企业微信**: Webhook API
- **SMTP 服务器**: 用于邮件通知

### 基础设施依赖
- **MySQL 5.7+**: 持久化存储
- **Redis 5.0+**: 缓存和分布式协调
- **Docker/Kubernetes**: 容器化部署

### Python 核心依赖
- `fastapi`: Web 框架
- `sqlalchemy`: ORM
- `redis`: Redis 客户端
- `prometheus-api-client`: Prometheus 查询客户端
- `httpx`: 异步 HTTP 客户端（用于 Webhook）
- `apscheduler`: 定时任务调度
- `python-jose`: JWT 认证
- `passlib`: 密码加密
