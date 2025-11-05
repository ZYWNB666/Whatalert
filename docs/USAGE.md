# 使用指南

## 快速开始

### 1. 环境准备

```bash
# Python 3.11+
python --version

# PostgreSQL 14+ 或 MySQL 8+
# Redis 6+
```

### 2. 安装依赖

```bash
cd alert_system
pip install -r requirements.txt
```

### 3. 配置

```bash
# 复制配置文件
cp config/config.example.yaml config/config.yaml

# 修改数据库连接信息
vim config/config.yaml
```

配置示例:
```yaml
database:
  type: "postgresql"
  host: "localhost"
  port: 5432
  username: "alert_user"
  password: "your_password"
  database: "alert_system"

redis:
  host: "localhost"
  port: 6379
  password: ""
```

### 4. 初始化数据库

```bash
python scripts/init_db.py
```

输出:
```
✅ 数据库表创建成功
✅ 默认数据创建成功

默认账户信息:
  管理员: admin / admin123
  测试用户: test / test123

🎉 数据库初始化完成!
```

### 5. 启动服务

```bash
# 开发模式
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 生产模式
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000
```

### 6. 访问

- **API 文档**: http://localhost:8000/docs
- **健康检查**: http://localhost:8000/health

## API 使用

### 认证

#### 登录获取 Token

```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin123"
```

响应:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

#### 获取当前用户信息

```bash
curl -X GET "http://localhost:8000/api/v1/auth/me" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 告警规则管理

#### 创建告警规则

```bash
curl -X POST "http://localhost:8000/api/v1/alert-rules/" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "CPU使用率过高",
    "description": "当CPU使用率超过80%时告警",
    "expr": "100 - (avg by (instance) (irate(node_cpu_seconds_total{mode=\"idle\"}[5m])) * 100)",
    "eval_interval": 60,
    "for_duration": 120,
    "severity": "warning",
    "labels": {
      "team": "backend",
      "service": "api"
    },
    "annotations": {
      "summary": "实例 {{instance}} CPU使用率为 {{value}}%",
      "description": "CPU使用率已超过80%，当前值: {{value}}%"
    },
    "route_config": {
      "notification_channels": [1, 2]
    },
    "datasource_id": 1
  }'
```

#### 查询告警规则

```bash
# 获取列表
curl -X GET "http://localhost:8000/api/v1/alert-rules/" \
  -H "Authorization: Bearer YOUR_TOKEN"

# 获取详情
curl -X GET "http://localhost:8000/api/v1/alert-rules/1" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

#### 更新告警规则

```bash
curl -X PUT "http://localhost:8000/api/v1/alert-rules/1" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "severity": "critical",
    "for_duration": 60
  }'
```

#### 删除告警规则

```bash
curl -X DELETE "http://localhost:8000/api/v1/alert-rules/1" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 查询告警事件

#### 查询当前告警

```bash
curl -X GET "http://localhost:8000/api/v1/alert-rules/events/current" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

响应:
```json
[
  {
    "id": 1,
    "fingerprint": "abc123def456",
    "rule_id": 1,
    "rule_name": "CPU使用率过高",
    "status": "firing",
    "severity": "warning",
    "started_at": 1704067200,
    "last_eval_at": 1704067260,
    "value": 85.5,
    "labels": {
      "instance": "server-01",
      "team": "backend"
    }
  }
]
```

#### 查询历史告警

```bash
curl -X GET "http://localhost:8000/api/v1/alert-rules/events/history?limit=50" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 静默规则管理

#### 创建静默规则

```bash
curl -X POST "http://localhost:8000/api/v1/silence/" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "测试环境静默",
    "description": "静默所有测试环境的告警",
    "matchers": [
      {
        "label": "environment",
        "operator": "=",
        "value": "test"
      }
    ],
    "starts_at": 1704067200,
    "ends_at": 1704153600,
    "comment": "维护期间静默"
  }'
```

**匹配器操作符说明:**
- `=`: 等于
- `!=`: 不等于
- `=~`: 正则匹配
- `!~`: 正则不匹配

#### 查询静默规则

```bash
curl -X GET "http://localhost:8000/api/v1/silence/" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

#### 删除静默规则

```bash
curl -X DELETE "http://localhost:8000/api/v1/silence/1" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## 配置示例

### 通知渠道配置

#### 飞书高级消息卡片

```json
{
  "name": "飞书-运维组",
  "type": "feishu",
  "config": {
    "webhook_url": "https://open.feishu.cn/open-apis/bot/v2/hook/xxx",
    "secret": "your-secret",
    "card_type": "advanced"
  },
  "filter_config": {
    "include_labels": {
      "severity": ["critical", "warning"]
    }
  }
}
```

#### 钉钉（带签名）

```json
{
  "name": "钉钉-研发组",
  "type": "dingtalk",
  "config": {
    "webhook_url": "https://oapi.dingtalk.com/robot/send?access_token=xxx",
    "secret": "your-secret"
  }
}
```

#### 企业微信

```json
{
  "name": "企微-测试组",
  "type": "wechat",
  "config": {
    "webhook_url": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx"
  }
}
```

#### 邮件

```json
{
  "name": "邮件-管理员",
  "type": "email",
  "config": {
    "to": ["admin@example.com", "ops@example.com"],
    "cc": ["manager@example.com"],
    "subject_prefix": "[生产告警]"
  }
}
```

### 告警路由配置

```json
{
  "route_config": {
    "match_labels": {
      "environment": "production",
      "team": "backend"
    },
    "notification_channels": [1, 2, 3]
  }
}
```

**路由规则:**
1. 如果告警标签匹配 `match_labels`，发送到指定渠道
2. 如果不匹配，使用默认渠道
3. 支持标签过滤（include_labels, exclude_labels）

### 静默规则示例

#### 基于时间的静默

```json
{
  "name": "夜间静默-低优先级告警",
  "matchers": [
    {
      "label": "severity",
      "operator": "=",
      "value": "info"
    }
  ],
  "starts_at": 1704067200,  // 每晚22:00
  "ends_at": 1704081600     // 次日06:00
}
```

#### 基于标签的静默

```json
{
  "name": "静默测试环境",
  "matchers": [
    {
      "label": "environment",
      "operator": "=~",
      "value": "test|dev"
    }
  ]
}
```

## 最佳实践

### 1. 告警规则设计

- **命名规范**: 使用清晰的描述性名称
- **标签设计**: 合理使用标签进行分类
- **持续时间**: 避免瞬时抖动，设置合理的 `for_duration`
- **注释模板**: 使用变量提供详细信息

### 2. 通知策略

- **分级通知**: 不同严重程度使用不同渠道
- **避免告警风暴**: 合理设置通知间隔
- **标签过滤**: 只发送相关告警给对应团队

### 3. 静默管理

- **临时静默**: 维护期间使用 API 快速静默
- **定期静默**: 非工作时间静默低优先级告警
- **文档记录**: 添加详细的静默原因

### 4. 权限管理

- **最小权限**: 普通用户只分配必要权限
- **角色分离**: 区分管理员、运维、开发等角色
- **定期审计**: 检查权限分配和使用情况

## 故障排查

### 告警未触发

1. 检查规则是否启用
2. 检查数据源连接
3. 查看评估日志
4. 验证 PromQL 语法

### 通知未发送

1. 检查静默规则
2. 验证通知渠道配置
3. 查看通知记录
4. 检查标签过滤规则

### 性能问题

1. 优化 PromQL 查询
2. 调整评估间隔
3. 增加数据库索引
4. 启用 Redis 缓存

## 监控指标

系统本身也应该被监控，建议监控以下指标:

- **规则评估延迟**: 评估耗时
- **通知成功率**: 发送成功/失败比例
- **数据库连接数**: 连接池使用情况
- **API 响应时间**: 接口性能
- **告警数量**: 当前活跃告警数

## 更多信息

- GitHub: https://github.com/your-repo/alert-system
- 文档: https://docs.example.com
- 问题反馈: https://github.com/your-repo/alert-system/issues

