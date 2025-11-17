## MODIFIED Requirements

### Requirement: 静默规则标签匹配
系统 SHALL 支持基于标签的灵活静默规则匹配，兼容 Alertmanager 匹配语法。

#### Scenario: 精确匹配标签
- **WHEN** 静默规则配置 matcher `{"label": "alertname", "operator": "=", "value": "HighCPU"}`
- **AND** 告警标签包含 `alertname=HighCPU`
- **THEN** 告警匹配该静默规则

#### Scenario: 不等于匹配
- **WHEN** 静默规则配置 matcher `{"label": "environment", "operator": "!=", "value": "production"}`
- **AND** 告警标签 environment 不等于 production（或不存在该标签）
- **THEN** 告警匹配该静默规则

#### Scenario: 正则表达式匹配
- **WHEN** 静默规则配置 matcher `{"label": "severity", "operator": "=~", "value": "warning|critical"}`
- **AND** 告警标签 severity 为 warning 或 critical
- **THEN** 告警匹配该静默规则

#### Scenario: 正则表达式不匹配
- **WHEN** 静默规则配置 matcher `{"label": "team", "operator": "!~", "value": "^test.*"}`
- **AND** 告警标签 team 不以 test 开头
- **THEN** 告警匹配该静默规则

#### Scenario: 多个 matcher AND 逻辑
- **WHEN** 静默规则配置多个 matchers：
  ```json
  [
    {"label": "alertname", "operator": "=", "value": "HighCPU"},
    {"label": "severity", "operator": "=~", "value": "warning|critical"}
  ]
  ```
- **AND** 告警同时满足 alertname=HighCPU 且 severity 为 warning 或 critical
- **THEN** 告警匹配该静默规则
- **AND** 如果任一 matcher 不匹配，则告警不匹配该规则

#### Scenario: 标签不存在时的匹配行为
- **WHEN** 静默规则配置 matcher `{"label": "pod", "operator": "=", "value": "app-pod"}`
- **AND** 告警不包含 pod 标签
- **THEN** 告警不匹配该静默规则（视为空字符串）

#### Scenario: 正则表达式语法错误处理
- **WHEN** 静默规则配置 matcher `{"label": "name", "operator": "=~", "value": "[invalid("}`
- **AND** 正则表达式语法无效
- **THEN** 系统在保存时返回错误提示
- **AND** 提示用户修正正则表达式

### Requirement: 静默规则时间范围检查
系统 SHALL 在检查静默规则时验证当前时间是否在静默时间范围内。

#### Scenario: 在静默时间范围内
- **WHEN** 静默规则 starts_at=1732000000, ends_at=1732100000
- **AND** 当前时间戳为 1732050000（在范围内）
- **AND** 告警匹配 matchers
- **THEN** 告警被静默

#### Scenario: 超出静默时间范围
- **WHEN** 静默规则 starts_at=1732000000, ends_at=1732100000
- **AND** 当前时间戳为 1732200000（已过期）
- **AND** 告警匹配 matchers
- **THEN** 告警不被静默
- **AND** 系统可选择自动禁用或删除过期规则

#### Scenario: 静默规则未启用
- **WHEN** 静默规则 is_enabled=False
- **AND** 告警匹配 matchers 且在时间范围内
- **THEN** 告警不被静默
