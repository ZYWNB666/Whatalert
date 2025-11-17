# Change: 增强监控功能 - 静默标签匹配、项目隔离、告警规则测试

## Why

当前系统存在以下功能缺陷：

1. **静默规则功能不完善**：虽然已有 matchers 字段支持标签匹配，但实际使用中缺乏像 Alertmanager 一样灵活的标签匹配能力，影响用户体验。

2. **缺少项目级别隔离**：目前只有租户级别的隔离，但实际场景中，同一租户下可能有多个项目（如前端项目、后端项目、移动端项目等），需要项目级别的数据隔离和权限控制。

3. **告警规则测试不便**：用户在编辑告警规则时，需要保存后才能看到效果，无法在编辑时即时测试 PromQL 表达式是否正确，以及会匹配到哪些数据，导致调试困难。

这三个功能是监控系统的核心用户体验，急需完善。

## What Changes

### 1. 静默规则标签匹配增强
- ✅ 保留现有 matchers 数据结构
- ✅ 增强静默检查逻辑，支持正则表达式匹配（=~, !~）
- ✅ 支持多个 matcher 的 AND 逻辑组合
- ✅ 前端优化：提供友好的标签选择和匹配规则配置界面

### 2. 项目隔离机制（新增）
- **新增 Project 模型**：在租户下创建项目层级
- **数据隔离**：告警规则、数据源、通知渠道、静默规则等关联到项目
- **权限控制**：用户可以属于多个项目，每个项目有独立的权限
- **向后兼容**：保留 tenant_id，新增 project_id 字段（可为空）
- **默认行为**：未指定项目时，使用租户级别的默认项目

### 3. 告警规则测试功能（新增）
- **测试接口**：提供 POST /api/v1/alert-rules/test 接口
- **实时查询**：执行 PromQL 查询，返回前 10 条匹配结果
- **结果展示**：显示标签、值、时间戳等详细信息
- **错误提示**：查询语法错误时返回友好的错误信息
- **前端集成**：在规则编辑页面添加"测试"按钮，显示测试结果面板

## Impact

### Affected specs
- `silence` - 增强标签匹配逻辑
- `project-isolation` - 新增项目隔离能力（新规范）
- `alert-rule-testing` - 新增告警规则测试能力（新规范）

### Affected code

#### Backend
- `app/models/` - 新增 Project 模型，更新其他模型添加 project_id
- `app/api/alert_rules.py` - 新增测试接口
- `app/api/silence.py` - 增强静默检查逻辑
- `app/services/alert_manager.py` - 更新静默检查方法
- `app/schemas/` - 新增 Project schema，更新测试相关 schema

#### Frontend
- `web/src/views/Silence/index.vue` - 优化静默规则配置界面
- `web/src/views/AlertRules/Create.vue` - 添加测试按钮和结果展示
- `web/src/api/` - 新增项目管理和测试相关 API
- `web/src/views/Projects/` - 新增项目管理页面

#### Database
- 新增 `project` 表
- 相关表添加 `project_id` 字段（允许 NULL，保持向后兼容）

### Breaking Changes
**无破坏性变更** - 所有新增字段设为可选，保持向后兼容。

### Migration Notes
1. 数据库迁移脚本会为现有数据创建默认项目
2. 现有租户下自动创建名为"默认项目"的 project
3. 所有现有数据关联到默认项目
