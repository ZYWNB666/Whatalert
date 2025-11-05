# 功能特性详解

## 1. 告警规则管理

### 核心能力

#### 多数据源支持
- **Prometheus**: 原生支持，完整的 PromQL 语法
- **VictoriaMetrics**: 兼容 Prometheus API
- **扩展性**: 易于添加新的 Metrics 数据源

#### PromQL 表达式
支持所有 Prometheus 查询表达式：

```promql
# CPU 使用率
100 - (avg by (instance) (irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)

# 内存使用率
(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100

# HTTP 错误率
rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m]) * 100
```

#### 自定义告警路由
基于标签的智能路由分发：

```json
{
  "route_config": {
    "match_labels": {
      "team": "backend",
      "environment": "production"
    },
    "notification_channels": [1, 2, 3]
  }
}
```

**路由逻辑:**
1. 匹配告警标签与路由配置
2. 符合条件的告警发送到指定渠道
3. 不匹配的使用默认渠道

#### 持续时间控制
避免瞬时抖动，告警需持续一定时间才触发：

```
状态流转:
pending (满足条件但未达持续时间)
   ↓ (达到 for_duration)
firing (正式告警，发送通知)
```

## 2. 告警抑制（静默）

### 两种静默方式

#### 方式一：规则配置静默

通过 Web 界面或 API 创建静默规则，基于标签匹配：

```json
{
  "name": "测试环境静默",
  "matchers": [
    {
      "label": "environment",
      "operator": "=",
      "value": "test"
    },
    {
      "label": "severity",
      "operator": "=~",
      "value": "warning|info"
    }
  ],
  "starts_at": 1704067200,
  "ends_at": 1704153600
}
```

#### 方式二：API 快速静默

```bash
# 快速创建静默（维护期间）
curl -X POST "http://localhost:8000/api/v1/silence/" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "name": "紧急维护静默",
    "matchers": [{"label": "instance", "operator": "=", "value": "server-01"}],
    "starts_at": 1704067200,
    "ends_at": 1704070800
  }'
```

### 匹配器操作符

- `=`: 精确匹配
- `!=`: 不等于
- `=~`: 正则匹配（支持 `warning|critical`）
- `!~`: 正则不匹配

### 静默优先级

静默检查在通知发送前执行，任何匹配静默规则的告警都不会发送通知。

## 3. 告警推送

### 飞书 (Feishu)

#### 高级消息卡片
支持飞书官方的 Interactive Card JSON 格式：

```json
{
  "msg_type": "interactive",
  "card": {
    "config": {
      "wide_screen_mode": true
    },
    "header": {
      "title": {
        "content": "🔔 告警触发",
        "tag": "plain_text"
      },
      "template": "red"
    },
    "elements": [
      {
        "tag": "div",
        "text": {
          "content": "**告警名称**: CPU使用率过高\n**等级**: critical",
          "tag": "lark_md"
        }
      }
    ]
  }
}
```

**特性:**
- 彩色卡片头部（red/green/blue）
- Markdown 格式化
- 交互按钮（可扩展）
- 美观的视觉效果

### 钉钉 (DingTalk)

支持签名认证（安全模式）：

```python
# 自动计算签名
timestamp = str(round(time.time() * 1000))
sign = hmac_sha256(secret, f'{timestamp}\n{secret}')
url = f"{webhook_url}&timestamp={timestamp}&sign={sign}"
```

### 企业微信 (WeChat Work)

支持文本和 Markdown 格式：

```json
{
  "msgtype": "markdown",
  "markdown": {
    "content": "# 告警触发\n**规则**: CPU使用率过高\n**等级**: <font color=\"warning\">critical</font>"
  }
}
```

### 邮件 (Email)

HTML 模板，专业美观：

```html
<div style="background: #f56c6c; color: white; padding: 20px;">
  <h1>告警触发</h1>
</div>
<div style="padding: 20px;">
  <h2>CPU使用率过高</h2>
  <table>
    <tr><td>等级</td><td>critical</td></tr>
    <tr><td>当前值</td><td>85.5%</td></tr>
  </table>
</div>
```

### 标签过滤

#### Include Labels（仅包含）
只发送包含特定标签的告警：

```json
{
  "include_labels": {
    "severity": ["critical", "warning"],
    "environment": ["production"]
  }
}
```

#### Exclude Labels（排除）
排除包含特定标签的告警：

```json
{
  "exclude_labels": {
    "team": ["test"],
    "temporary": ["true"]
  }
}
```

## 4. 告警查询

### 当前告警
查询所有活跃的告警事件（pending/firing 状态）：

```bash
GET /api/v1/alert-rules/events/current
```

**响应:**
```json
[
  {
    "fingerprint": "abc123",
    "rule_name": "CPU使用率过高",
    "status": "firing",
    "severity": "critical",
    "started_at": 1704067200,
    "value": 85.5,
    "labels": {...}
  }
]
```

### 历史告警
查询已恢复的告警，包含持续时间：

```bash
GET /api/v1/alert-rules/events/history
```

**响应:**
```json
[
  {
    "fingerprint": "xyz789",
    "rule_name": "内存使用率过高",
    "started_at": 1704060000,
    "resolved_at": 1704067200,
    "duration": 7200,  // 2小时
    "labels": {...}
  }
]
```

## 5. 多租户支持

### 数据隔离
所有数据都通过 `tenant_id` 隔离：

```sql
-- 查询时自动添加租户过滤
SELECT * FROM alertrule WHERE tenant_id = ?
```

### 配额管理
每个租户可设置独立配额：

```json
{
  "max_users": 100,
  "max_alert_rules": 1000,
  "max_datasources": 50,
  "max_notification_channels": 20
}
```

### 权限隔离
用户只能访问所属租户的资源：

```python
# 中间件自动注入租户ID
current_user.tenant_id -> 所有查询自动过滤
```

## 6. 日志审计

### 记录内容

- **操作类型**: create, update, delete, login
- **资源信息**: 资源类型、ID、名称
- **用户信息**: 用户ID、用户名
- **请求信息**: IP 地址、User-Agent、请求路径
- **变更内容**: 操作前后的数据对比
- **结果状态**: 成功/失败

### 审计示例

```json
{
  "action": "create",
  "resource_type": "alert_rule",
  "resource_id": 123,
  "resource_name": "CPU使用率过高",
  "user_id": 1,
  "username": "admin",
  "ip_address": "192.168.1.100",
  "changes": {
    "new": {"name": "CPU使用率过高", "severity": "critical"}
  },
  "status": "success",
  "timestamp": 1704067200
}
```

### 查询审计日志

```bash
# 按用户查询
GET /api/v1/audit?user_id=1

# 按资源类型查询
GET /api/v1/audit?resource_type=alert_rule

# 按时间范围查询
GET /api/v1/audit?start_time=1704067200&end_time=1704153600
```

## 7. 用户和角色管理

### RBAC 模型

```
User (用户)
  ↓ N:N
Role (角色)
  ↓ N:N
Permission (权限)
```

### 权限格式

`resource:action` 格式：

- `alert_rule:create` - 创建告警规则
- `alert_rule:read` - 查看告警规则
- `alert_rule:update` - 更新告警规则
- `alert_rule:delete` - 删除告警规则
- `datasource:*` - 数据源所有权限

### 角色示例

#### 管理员角色
拥有所有权限：
```json
{
  "name": "管理员",
  "code": "admin",
  "permissions": ["*:*"]
}
```

#### 运维角色
拥有告警管理权限：
```json
{
  "name": "运维",
  "code": "ops",
  "permissions": [
    "alert_rule:*",
    "silence:*",
    "datasource:read"
  ]
}
```

#### 只读角色
只能查看：
```json
{
  "name": "只读用户",
  "code": "viewer",
  "permissions": [
    "alert_rule:read",
    "datasource:read",
    "audit_log:read"
  ]
}
```

### 权限检查

```python
# 装饰器方式
@has_permission("alert_rule:create")
async def create_alert_rule(...):
    pass

# 手动检查
if not await permission_checker.has_permission(user, db):
    raise HTTPException(403, "No permission")
```

## 高级特性

### 1. 告警指纹机制

基于规则ID和标签生成唯一标识：

```python
fingerprint = md5(f"{rule_id}:{sorted_labels}")
```

**作用:**
- 唯一标识告警
- 追踪告警状态
- 避免重复通知

### 2. 通知频率控制

避免告警风暴：

```python
# 最小通知间隔（默认5分钟）
if current_time - last_sent_time < 300:
    return  # 不发送
```

### 3. 变量模板

注释支持变量替换：

```json
{
  "annotations": {
    "summary": "实例 {{instance}} CPU使用率为 {{value}}%",
    "description": "当前值: {{value}}，阈值: 80%"
  }
}
```

渲染结果：
```
实例 server-01 CPU使用率为 85.5%
当前值: 85.5，阈值: 80%
```

### 4. 异步架构

全异步处理，高并发性能：

```python
# 并发评估规则
tasks = [evaluate_rule(rule) for rule in rules]
await asyncio.gather(*tasks)

# 异步通知发送
async with httpx.AsyncClient() as client:
    await client.post(webhook_url, json=message)
```

## Web 界面特性

### 1. 现代化 UI
- Element Plus 组件库
- 响应式布局
- 深色侧边栏
- 美观的统计卡片

### 2. 实时更新
- 当前告警自动刷新（30秒）
- WebSocket 支持（可扩展）
- 实时状态展示

### 3. 交互体验
- 表单验证
- 操作确认
- Loading 状态
- 错误提示

### 4. 代码编辑器
- CodeMirror 集成（可选）
- PromQL 语法高亮
- 自动补全（可扩展）

## 扩展建议

### 短期 (1-2周)
- [ ] 完善数据源管理界面
- [ ] 完善通知渠道管理
- [ ] 添加告警规则模板
- [ ] 支持批量操作

### 中期 (1-2月)
- [ ] 集成 Grafana
- [ ] 支持 Loki 日志告警
- [ ] 告警聚合功能
- [ ] 移动端适配

### 长期 (3-6月)
- [ ] AI 智能分析
- [ ] 自动化运维
- [ ] SLA 管理
- [ ] 知识库集成

## 对比 WatchAlert

| 功能 | WatchAlert | 本系统 | 说明 |
|------|-----------|--------|------|
| 多租户 | ✅ | ✅ | 完整支持 |
| Metrics | ✅ | ✅ | Prometheus/VM |
| Logs | ✅ | ⏳ | 计划中 |
| Traces | ✅ | ⏳ | 计划中 |
| 静默规则 | ✅ | ✅ | 功能一致 |
| 通知渠道 | ✅ | ✅ | 飞书/钉钉/企微/邮件 |
| 告警升级 | ✅ | ⏳ | 可扩展 |
| AI 分析 | ✅ | ⏳ | 可扩展 |
| 语言 | Go | Python | 各有优势 |
| 性能 | 高 | 中 | Python 异步已优化 |

## 总结

这是一个功能完整、架构清晰的 Python 监控告警系统，完全满足你的需求：

1. ✅ 告警规则 + 多数据源 + 自定义路由
2. ✅ 告警抑制（规则配置 + API 静默）
3. ✅ 多渠道推送（飞书高级卡片 + 标签过滤）
4. ✅ 当前告警 + 历史告警查询
5. ✅ 完整的多租户支持
6. ✅ Metrics 告警（Prometheus/VictoriaMetrics）
7. ✅ 日志审计（操作记录 + 追溯）
8. ✅ 用户管理 + RBAC 权限

**额外亮点:**
- 现代化 Web 界面（Vue 3 + Element Plus）
- 异步架构（高性能）
- 完整文档（架构、使用、部署）
- 生产就绪（Docker/Systemd 部署方案）

