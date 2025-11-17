## ADDED Requirements

### Requirement: 告警规则测试接口
系统 SHALL 提供 API 接口用于测试告警规则的 PromQL 表达式。

#### Scenario: 测试成功返回匹配数据
- **WHEN** 用户提交测试请求，包含 datasource_id 和 expr
- **AND** PromQL 表达式语法正确
- **AND** 查询成功返回数据
- **THEN** 系统返回前 10 条匹配结果
- **AND** 每条结果包含 metric（标签）、value（值）、timestamp（时间戳）
- **AND** 返回总匹配数量和查询耗时

#### Scenario: 测试成功但无匹配数据
- **WHEN** PromQL 查询成功执行
- **AND** 没有匹配到任何数据
- **THEN** 系统返回 success=true
- **AND** result_count=0
- **AND** 提示消息"查询成功，但没有匹配到任何数据"

#### Scenario: PromQL 语法错误
- **WHEN** 用户提交的 PromQL 表达式语法错误
- **THEN** 系统返回 success=false
- **AND** 返回错误信息，如"parse error: unexpected character"
- **AND** error_type 标记为 "syntax"

#### Scenario: 数据源连接失败
- **WHEN** 配置的数据源无法连接
- **THEN** 系统返回 success=false
- **AND** 返回错误信息，如"connection timeout"
- **AND** error_type 标记为 "connection"

#### Scenario: 查询超时
- **WHEN** PromQL 查询执行超过 5 秒
- **THEN** 系统中断查询
- **AND** 返回超时错误
- **AND** 建议用户优化查询表达式

### Requirement: 测试结果格式化
系统 SHALL 格式化测试结果，便于前端展示。

#### Scenario: 格式化时序数据
- **WHEN** Prometheus 返回时序数据
- **THEN** 系统解析 metric 标签
- **AND** 提取 value 和 timestamp
- **AND** 转换为易读的 JSON 格式

#### Scenario: 限制返回数量
- **WHEN** PromQL 查询匹配超过 10 条数据
- **THEN** 只返回前 10 条详细数据
- **AND** result_count 字段显示实际总数
- **AND** 提示用户"显示前 10 条，共 X 条"

#### Scenario: 标签排序
- **WHEN** 返回 metric 标签
- **THEN** 标签按字母顺序排序
- **AND** 重要标签（如 alertname, instance）优先显示

### Requirement: 测试接口权限和限流
系统 SHALL 对测试接口进行权限验证和速率限制。

#### Scenario: 权限验证
- **WHEN** 用户测试告警规则
- **THEN** 验证用户有数据源的访问权限
- **AND** 验证用户在对应项目中有权限
- **AND** 未授权用户返回 403 错误

#### Scenario: 速率限制
- **WHEN** 用户在 1 分钟内测试次数超过 10 次
- **THEN** 系统返回 429 Too Many Requests
- **AND** 提示用户"测试频率过高，请稍后再试"
- **AND** 返回 Retry-After 头指示重试时间

#### Scenario: 用户级别限流
- **WHEN** 计算测试频率
- **THEN** 基于用户 ID + IP 地址
- **AND** 不同用户独立计数
- **AND** 使用 Redis 实现分布式限流

### Requirement: 前端测试功能集成
系统 SHALL 在告警规则编辑页面提供测试按钮和结果展示。

#### Scenario: 测试按钮位置
- **WHEN** 用户在告警规则编辑页面
- **THEN** 测试按钮显示在更新和取消按钮旁边
- **AND** 按钮文本为"测试"
- **AND** 图标为播放或实验图标

#### Scenario: 测试结果面板展示
- **WHEN** 用户点击测试按钮
- **THEN** 在表单下方展开测试结果面板
- **AND** 显示加载状态（查询中...）
- **AND** 查询完成后显示结果或错误信息

#### Scenario: 成功结果展示
- **WHEN** 测试成功返回数据
- **THEN** 显示绿色成功图标
- **AND** 显示"查询成功，匹配到 X 条数据（耗时 Y 秒）"
- **AND** 列表展示每条数据的标签和值
- **AND** 支持展开/折叠每条数据详情

#### Scenario: 错误结果展示
- **WHEN** 测试返回错误
- **THEN** 显示红色错误图标
- **AND** 显示错误类型和错误信息
- **AND** 语法错误高亮显示错误位置（如果可能）
- **AND** 提供帮助链接指向 PromQL 文档

#### Scenario: 无数据展示
- **WHEN** 测试成功但无匹配数据
- **THEN** 显示黄色警告图标
- **AND** 提示"查询成功，但没有匹配到任何数据"
- **AND** 建议用户检查查询表达式或数据源

#### Scenario: 测试按钮状态管理
- **WHEN** 用户点击测试按钮
- **THEN** 按钮变为禁用状态，显示"测试中..."
- **AND** 查询完成后恢复可用状态
- **AND** 如果 PromQL 表达式或数据源未填写，按钮禁用

### Requirement: 测试结果清除
系统 SHALL 允许用户清除测试结果面板。

#### Scenario: 清除测试结果
- **WHEN** 用户点击"清除"或"关闭"按钮
- **THEN** 测试结果面板关闭或清空
- **AND** 用户可以重新执行测试

#### Scenario: 切换规则时清除结果
- **WHEN** 用户切换到其他告警规则
- **THEN** 自动清除之前的测试结果
- **AND** 避免显示不相关的测试数据
