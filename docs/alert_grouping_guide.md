# 告警分组和静默功能使用指南

## 功能概述

系统现在支持两个重要功能：

### 1. 告警合并（Alert Grouping）
类似于 Alertmanager 的告警分组功能，可以将相同规则和相同标签的告警合并成一条通知，避免告警风暴。

### 2. 基于 Label 的静默（Silence）
支持基于标签匹配的告警静默规则，可以精准地静默特定标签的告警。

---

## 一、告警分组功能

### 1.1 工作原理

告警分组的工作流程：

1. **分组规则**：按照规则名称 + 指定的 labels 进行分组
2. **等待时间**：告警会在分组中等待 `group_wait` 时间（默认 10 秒）
3. **批量发送**：等待时间到达后，将同一组的所有告警合并成一条通知发送
4. **重复通知**：如果告警持续，会按照 `repeat_interval`（默认 1 小时）重复发送

### 1.2 配置分组

#### 在告警规则中配置分组

在创建或更新告警规则时，可以在 `route_config` 中配置：

```json
{
  "name": "高CPU告警",
  "expr": "cpu_usage > 80",
  "route_config": {
    "enable_grouping": true,         // 是否启用分组（默认 true）
    "group_by": ["hostname", "env"],  // 按照哪些 label 分组
    "notification_channels": [1, 2, 3]
  }
}
```

**group_by 说明**：
- 如果不设置 `group_by`，只按规则名称分组
- 设置 `group_by: ["hostname", "env"]` 后，只有规则名称、hostname 和 env 都相同的告警才会合并

#### 全局分组参数配置

系统启动时会自动配置分组参数（在 `app/main.py` 中）：

```python
alert_manager.configure_grouper(
    group_wait=10,       # 分组等待时间（秒）
    group_interval=30,   # 分组间隔（秒）
    repeat_interval=3600 # 重复发送间隔（秒）
)
```

### 1.3 查看分组统计

通过 API 查看当前分组状态：

```bash
GET /api/v1/alert-rules/grouping/stats
```

返回示例：
```json
{
  "total_groups": 5,
  "total_alerts": 12,
  "sent_groups": 2,
  "pending_groups": 3
}
```

### 1.4 通知格式

合并后的告警通知会显示：
- 告警规则名称
- 告警总数
- 每条告警的详细信息（等级、值、标签等）

支持的通知渠道都会自动适配批量格式：
- 飞书：显示合并的卡片（最多显示 10 条）
- 钉钉/企业微信：显示文本列表（最多显示 20 条）
- 邮件：HTML 格式展示（最多显示 50 条）
- Webhook：类似 Alertmanager 格式，包含所有告警

---

## 二、基于 Label 的静默功能

### 2.1 静默规则说明

静默规则通过 `matchers` 来匹配告警的 labels，只有匹配的告警才会被静默。

### 2.2 创建静默规则

```bash
POST /api/v1/silence/
```

请求示例：
```json
{
  "name": "维护窗口 - 生产环境 Web 服务器",
  "description": "计划内维护",
  "matchers": [
    {
      "label": "env",
      "operator": "=",
      "value": "production"
    },
    {
      "label": "service",
      "operator": "=",
      "value": "web"
    }
  ],
  "starts_at": 1699200000,
  "ends_at": 1699210800,
  "is_enabled": true,
  "comment": "系统升级维护"
}
```

### 2.3 匹配器（Matchers）

支持的操作符：

| 操作符 | 说明 | 示例 |
|--------|------|------|
| `=` | 等于 | `{"label": "env", "operator": "=", "value": "prod"}` |
| `!=` | 不等于 | `{"label": "severity", "operator": "!=", "value": "info"}` |
| `=~` | 正则匹配 | `{"label": "hostname", "operator": "=~", "value": "web-.*"}` |
| `!~` | 正则不匹配 | `{"label": "service", "operator": "!~", "value": "test-.*"}` |

### 2.4 匹配逻辑

- **AND 逻辑**：多个 matchers 之间是 AND 关系，必须全部匹配才会静默
- 告警的 label 必须包含 matcher 中的 label
- 如果告警缺少某个 label，则不匹配

### 2.5 静默规则示例

#### 示例 1：静默特定主机
```json
{
  "name": "静默主机 web-01",
  "matchers": [
    {"label": "hostname", "operator": "=", "value": "web-01"}
  ],
  "starts_at": 1699200000,
  "ends_at": 1699210800
}
```

#### 示例 2：静默测试环境的所有告警
```json
{
  "name": "静默测试环境",
  "matchers": [
    {"label": "env", "operator": "=", "value": "test"}
  ],
  "starts_at": 1699200000,
  "ends_at": 1699296000
}
```

#### 示例 3：静默特定告警类型
```json
{
  "name": "静默磁盘告警",
  "matchers": [
    {"label": "alertname", "operator": "=~", "value": "Disk.*"}
  ],
  "starts_at": 1699200000,
  "ends_at": 1699210800
}
```

#### 示例 4：静默生产环境的特定服务
```json
{
  "name": "静默生产数据库",
  "matchers": [
    {"label": "env", "operator": "=", "value": "production"},
    {"label": "service", "operator": "=", "value": "database"}
  ],
  "starts_at": 1699200000,
  "ends_at": 1699210800
}
```

### 2.6 管理静默规则

#### 查看所有静默规则
```bash
GET /api/v1/silence/
```

#### 删除静默规则
```bash
DELETE /api/v1/silence/{rule_id}
```

---

## 三、最佳实践

### 3.1 告警分组最佳实践

1. **合理设置 group_by**
   - 对于主机相关告警：`["hostname"]`
   - 对于服务相关告警：`["service", "env"]`
   - 对于集群相关告警：`["cluster", "namespace"]`

2. **调整等待时间**
   - 短时间告警（如瞬时抖动）：`group_wait=30s`
   - 一般告警：`group_wait=10s`（默认）
   - 慢速告警（如定时任务）：`group_wait=60s`

3. **分组策略示例**

   **场景 1：主机监控**
   ```json
   {
     "group_by": ["hostname"],
     "enable_grouping": true
   }
   ```
   效果：同一台主机的多个告警（CPU、内存、磁盘）会合并成一条通知

   **场景 2：微服务监控**
   ```json
   {
     "group_by": ["service", "env", "region"],
     "enable_grouping": true
   }
   ```
   效果：同一服务、同一环境、同一区域的告警会合并

### 3.2 静默规则最佳实践

1. **计划内维护**
   ```json
   {
     "name": "周末维护窗口",
     "matchers": [
       {"label": "env", "operator": "=", "value": "production"}
     ],
     "starts_at": "维护开始时间",
     "ends_at": "维护结束时间"
   }
   ```

2. **临时问题抑制**
   - 已知问题正在修复中，暂时静默相关告警
   - 设置合理的结束时间，避免永久静默

3. **告警调试**
   - 新规则上线时，先静默一段时间观察
   - 确认无误后再取消静默

---

## 四、注意事项

1. **告警分组**
   - 分组只影响通知的发送方式，不影响告警本身的状态
   - 恢复通知不会被分组，会立即发送

2. **静默规则**
   - 被静默的告警仍然会记录在系统中
   - 静默只影响通知发送，不影响告警状态
   - 过期的静默规则会自动失效

3. **性能考虑**
   - 大量告警分组时，建议调整 `group_wait` 适当延长
   - 静默规则的正则匹配会有性能开销，建议使用精确匹配

---

## 五、故障排查

### 5.1 告警未合并

检查项：
1. 确认规则配置了 `enable_grouping: true`
2. 检查 `group_by` 配置的 labels 是否存在
3. 查看分组统计 API 确认分组是否创建

### 5.2 静默规则不生效

检查项：
1. 确认静默规则的时间范围包含当前时间
2. 检查 matchers 是否正确匹配告警的 labels
3. 确认静默规则的 `is_enabled` 为 `true`
4. 查看日志确认告警是否被静默：`"告警被静默: fingerprint=xxx"`

### 5.3 查看日志

关键日志关键词：
- 告警分组：`"创建新的告警分组"`, `"告警添加到分组"`
- 告警发送：`"发送告警分组"`, `"批量Webhook发送成功"`
- 静默规则：`"告警被静默"`

---

## 六、API 文档

### 6.1 告警分组 API

```bash
# 查看分组统计
GET /api/v1/alert-rules/grouping/stats

# 响应示例
{
  "total_groups": 5,      # 总分组数
  "total_alerts": 12,     # 总告警数
  "sent_groups": 2,       # 已发送分组数
  "pending_groups": 3     # 待发送分组数
}
```

### 6.2 静默规则 API

```bash
# 创建静默规则
POST /api/v1/silence/

# 获取静默规则列表
GET /api/v1/silence/

# 删除静默规则
DELETE /api/v1/silence/{rule_id}
```

---

## 七、总结

通过告警分组和基于 Label 的静默功能，你可以：

1. ✅ 避免告警风暴，减少重复通知
2. ✅ 精准控制告警静默，不影响其他告警
3. ✅ 灵活配置分组策略，适应不同场景
4. ✅ 支持计划内维护窗口
5. ✅ 提高告警通知的可读性和可管理性

这两个功能完全兼容现有系统，不需要修改现有的告警规则和通知渠道配置。

