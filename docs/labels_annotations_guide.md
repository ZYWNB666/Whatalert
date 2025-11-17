# 告警规则标签和注释使用指南

## 概述

在告警规则中，**标签（Labels）** 和 **注释（Annotations）** 是两个重要的元数据字段，用于丰富告警信息和控制告警行为。

---

## 标签（Labels）

### 作用
- 用于**告警分组**和**路由控制**
- 用于**筛选和过滤**告警
- 影响告警的**去重和分组**逻辑
- 作为**告警标识**的一部分

### 使用场景
1. **团队归属**：标识告警所属团队
   - `team: backend`
   - `team: frontend`

2. **服务标识**：标识具体服务
   - `service: api`
   - `service: database`

3. **环境区分**：区分不同部署环境
   - `env: production`
   - `env: staging`
   - `env: dev`

4. **区域信息**：标识地理位置或集群
   - `region: us-west`
   - `cluster: prod-k8s-01`

5. **优先级**：告警优先级
   - `priority: high`
   - `priority: low`

### 最佳实践

**✅ 推荐做法：**
```yaml
labels:
  team: backend
  service: user-api
  env: production
  region: us-west
```

**❌ 不推荐：**
- 不要在标签中放入长文本或描述性内容
- 不要使用动态变化的值（如时间戳）
- 避免使用特殊字符（建议使用字母、数字、下划线、短横线）

---

## 注释（Annotations）

### 作用
- 提供**告警的详细描述**
- 支持**模板变量**，动态显示告警信息
- 用于**通知消息**的内容展示
- 提供**相关链接**（如文档、仪表盘）

### 常用注释字段

#### 1. summary（摘要）
简短的告警描述，通常包含关键信息

**示例：**
```
summary: "服务 {{labels.service}} 在 {{labels.instance}} 上不可用"
```

**效果：**
```
服务 user-api 在 192.168.1.10:8080 上不可用
```

#### 2. description（详细描述）
更详细的告警说明，包含当前值、阈值等

**示例：**
```
description: "当前值: {{value}}，持续时间超过 {{labels.for_duration}} 秒"
```

**效果：**
```
当前值: 0.95，持续时间超过 300 秒
```

#### 3. runbook_url（处理手册链接）
指向故障排查文档或处理流程

**示例：**
```
runbook_url: "https://wiki.company.com/runbook/high-cpu"
```

#### 4. dashboard_url（仪表盘链接）
相关监控仪表盘的链接

**示例：**
```
dashboard_url: "https://grafana.company.com/d/service-health"
```

### 模板变量

注释支持使用以下模板变量：

| 变量 | 说明 | 示例 |
|------|------|------|
| `{{instance}}` | 实例标识 | `192.168.1.10:8080` |
| `{{value}}` | 当前告警值 | `0.95` |
| `{{labels.xxx}}` | 任何标签的值 | `{{labels.service}}` → `user-api` |
| `{{labels.alertname}}` | 告警规则名称 | `HighCPUUsage` |

### 使用场景

#### 场景1：服务不可用告警
```yaml
annotations:
  summary: "服务实例 {{labels.instance}} 不可用"
  description: "服务 {{labels.service}} 在 {{labels.instance}} 上已停止响应，当前值: {{value}}"
  runbook_url: "https://wiki.company.com/runbook/service-down"
  dashboard_url: "https://grafana.company.com/d/service-health?var-service={{labels.service}}"
```

#### 场景2：高CPU使用率告警
```yaml
annotations:
  summary: "{{labels.instance}} CPU使用率过高"
  description: "实例 {{labels.instance}} 的CPU使用率为 {{value}}%，已超过阈值 85%"
  runbook_url: "https://wiki.company.com/runbook/high-cpu"
```

#### 场景3：磁盘空间告警
```yaml
annotations:
  summary: "{{labels.instance}} 磁盘空间不足"
  description: "挂载点 {{labels.mountpoint}} 在 {{labels.instance}} 上的可用空间仅剩 {{value}}%"
  runbook_url: "https://wiki.company.com/runbook/disk-full"
```

---

## UI 使用说明

### 新版界面特性

1. **键值对表单**
   - 不再需要手动编写 JSON
   - 点击"添加标签"/"添加注释"按钮新增行
   - 填写标签名和标签值
   - 点击删除按钮移除不需要的行

2. **常用预设**
   - 标签预设：team、service、env、region、cluster
   - 注释预设：summary、description、runbook_url、dashboard_url
   - 点击预设后会自动添加到列表，填写具体值即可

3. **模板变量提示**
   - 在注释输入区域下方显示可用的模板变量
   - 支持：instance、value、labels.xxx 等

### 操作步骤

#### 添加标签
1. 点击"添加标签"按钮
2. 在"标签名"输入框填写，如：`team`
3. 在"标签值"输入框填写，如：`backend`
4. 重复以上步骤添加更多标签

#### 使用预设标签
1. 点击"常用标签"下拉菜单
2. 选择需要的预设项（如"team（团队）"）
3. 系统自动添加标签名，填写对应的值即可

#### 添加注释
1. 点击"添加注释"按钮
2. 在"注释名"输入框填写，如：`summary`
3. 在"注释值"输入框填写，支持模板变量，如：`服务 {{labels.service}} 告警`
4. 重复以上步骤添加更多注释

---

## 完整示例

### 示例1：Web服务监控

**标签：**
```
team: backend
service: web-api
env: production
region: us-west
priority: high
```

**注释：**
```
summary: Web API服务 {{labels.instance}} 响应异常
description: 服务响应时间为 {{value}}ms，已超过阈值 1000ms，持续时间超过5分钟
runbook_url: https://wiki.company.com/runbook/api-slow-response
dashboard_url: https://grafana.company.com/d/web-api-dashboard
```

### 示例2：数据库监控

**标签：**
```
team: dba
service: mysql
env: production
cluster: prod-db-cluster
priority: critical
```

**注释：**
```
summary: MySQL连接数过高 - {{labels.instance}}
description: 当前连接数为 {{value}}，已达到最大连接数的 90%
runbook_url: https://wiki.company.com/runbook/mysql-connections
dashboard_url: https://grafana.company.com/d/mysql-overview?instance={{labels.instance}}
```

---

## 注意事项

1. **标签会影响告警分组**
   - 相同标签的告警会被分为一组
   - 修改标签可能导致告警重新分组

2. **注释内容会出现在通知中**
   - 确保模板变量正确
   - 避免在注释中包含敏感信息

3. **模板变量仅在注释中有效**
   - 标签值不支持模板变量
   - 标签值应为静态字符串

4. **保持简洁**
   - 标签数量控制在 5-10 个以内
   - 注释内容简明扼要，重点突出

---

## 迁移指南

### 从旧版 JSON 格式迁移

**旧版（JSON）：**
```json
{
  "team": "backend",
  "service": "api"
}
```

**新版（键值对表单）：**
- 点击"添加标签"，填写 `team` = `backend`
- 再次点击"添加标签"，填写 `service` = `api`

系统会自动将表单转换为正确的格式保存到数据库。

---

## 常见问题

**Q: 标签和注释有什么区别？**
A: 标签用于告警的分组和筛选，是告警标识的一部分；注释用于提供详细信息，不影响告警分组。

**Q: 可以在标签中使用模板变量吗？**
A: 不可以。模板变量只能在注释中使用。

**Q: 如何在注释中引用标签？**
A: 使用 `{{labels.xxx}}` 格式，如 `{{labels.service}}`。

**Q: 预设的标签/注释可以修改吗？**
A: 可以。预设只是快速输入，添加后可以随意修改名称和值。

**Q: 删除标签/注释会影响历史告警吗？**
A: 不会。修改只影响新产生的告警，历史告警保持原有的标签和注释。
