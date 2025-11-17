## ADDED Requirements

### Requirement: 项目模型定义
系统 SHALL 支持在租户下创建项目，实现二级数据隔离。

#### Scenario: 创建项目
- **WHEN** 用户在租户下创建新项目
- **THEN** 系统创建项目记录，包含名称、代码、描述等信息
- **AND** 项目关联到当前租户
- **AND** 创建者自动成为项目 owner

#### Scenario: 项目代码唯一性
- **WHEN** 在同一租户下创建项目
- **THEN** 项目代码（code）必须在该租户内唯一
- **AND** 不同租户可以使用相同的项目代码

#### Scenario: 默认项目创建
- **WHEN** 系统首次为租户创建项目
- **THEN** 自动创建名为"默认项目"的项目
- **AND** 设置 is_default=True
- **AND** 租户下所有用户自动加入默认项目

### Requirement: 项目成员管理
系统 SHALL 支持管理项目成员及其角色。

#### Scenario: 添加项目成员
- **WHEN** 项目 owner 或 admin 添加用户到项目
- **THEN** 创建项目-用户关联记录
- **AND** 指定用户角色（owner/admin/member/viewer）
- **AND** 用户可以访问该项目的资源

#### Scenario: 用户可属于多个项目
- **WHEN** 用户被添加到多个项目
- **THEN** 用户可以在不同项目间切换
- **AND** 每个项目中可以有不同的角色

#### Scenario: 移除项目成员
- **WHEN** 项目 owner 移除用户
- **THEN** 删除项目-用户关联
- **AND** 用户失去该项目的访问权限
- **AND** 不能移除最后一个 owner

### Requirement: 项目级别数据隔离
系统 SHALL 将告警规则、数据源、通知渠道等资源关联到项目。

#### Scenario: 告警规则关联项目
- **WHEN** 创建告警规则
- **THEN** 告警规则必须关联到一个项目
- **AND** 只有该项目的成员可以查看和管理该规则

#### Scenario: 列出项目资源
- **WHEN** 用户查询告警规则列表
- **THEN** 只返回用户有权限的项目的规则
- **AND** 支持通过 project_id 参数过滤特定项目

#### Scenario: 跨项目查询（用户有多个项目权限）
- **WHEN** 用户属于多个项目
- **AND** 查询时不指定 project_id
- **THEN** 返回所有有权限的项目的资源
- **AND** 响应中包含 project_id 标识资源所属项目

### Requirement: 项目权限控制
系统 SHALL 基于项目角色控制用户操作权限。

#### Scenario: Owner 权限
- **WHEN** 用户在项目中角色为 owner
- **THEN** 可以执行所有操作（创建、编辑、删除、管理成员）
- **AND** 可以删除项目

#### Scenario: Admin 权限
- **WHEN** 用户在项目中角色为 admin
- **THEN** 可以创建、编辑、删除资源
- **AND** 可以管理项目成员（除 owner 外）
- **AND** 不能删除项目

#### Scenario: Member 权限
- **WHEN** 用户在项目中角色为 member
- **THEN** 可以创建和编辑自己创建的资源
- **AND** 可以查看项目内所有资源
- **AND** 不能删除他人创建的资源

#### Scenario: Viewer 权限
- **WHEN** 用户在项目中角色为 viewer
- **THEN** 只能查看项目内资源
- **AND** 不能创建、编辑或删除任何资源

### Requirement: 向后兼容迁移
系统 SHALL 支持现有数据无缝迁移到项目结构。

#### Scenario: 自动创建默认项目
- **WHEN** 系统升级时
- **THEN** 为每个现有租户自动创建默认项目
- **AND** 所有现有数据关联到默认项目
- **AND** 所有现有用户加入默认项目为 admin 角色

#### Scenario: 保持租户级别查询兼容
- **WHEN** API 查询未指定 project_id
- **THEN** 返回用户在该租户所有项目的数据
- **AND** 保持与旧版本 API 的兼容性

### Requirement: 项目配额管理
系统 SHALL 支持限制项目内的资源数量。

#### Scenario: 告警规则配额检查
- **WHEN** 项目设置 max_alert_rules=100
- **AND** 项目已有 100 条告警规则
- **AND** 用户尝试创建新规则
- **THEN** 系统返回错误提示"已达到项目告警规则配额上限"

#### Scenario: 无配额限制
- **WHEN** 项目未设置配额
- **THEN** 使用租户级别的配额限制
- **AND** 如果租户也未设置，则无限制
