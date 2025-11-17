# 项目隔离改造方案

## 问题分析
当前系统只实现了租户级隔离(tenant_id),但没有实现项目级隔离(project_id)。
用户在不同项目中的数据(告警规则、数据源、通知渠道、静默规则、告警事件)应该完全隔离。

## 数据库改造

### 1. 已有 project_id 的表
- alert_rule ✅
- datasource ✅  
- notification_channel ✅
- silence_rule ✅

### 2. 需要添加 project_id 的表
- alert_event ❌ (当前告警)
- alert_event_history ❌ (历史告警)

SQL 脚本: `scripts/add_project_isolation.sql`

## API 改造

### 需要改造的 API 文件

#### 1. app/api/alert_rules.py (告警规则)
所有接口需要添加 project_id 过滤:
- POST   /alert-rules/                  - 创建时设置 project_id
- GET    /alert-rules/                  - 列表按 project_id 过滤
- GET    /alert-rules/{rule_id}         - 详情验证 project_id
- PUT    /alert-rules/{rule_id}         - 更新验证 project_id
- DELETE /alert-rules/{rule_id}         - 删除验证 project_id
- POST   /alert-rules/test              - 测试验证 project_id
- GET    /alert-rules/events/current    - 当前告警按 project_id 过滤
- GET    /alert-rules/events/history    - 历史告警按 project_id 过滤

#### 2. app/api/datasources.py (数据源)
- POST   /datasources/                  - 创建时设置 project_id
- GET    /datasources/                  - 列表按 project_id 过滤
- GET    /datasources/{datasource_id}   - 详情验证 project_id
- PUT    /datasources/{datasource_id}   - 更新验证 project_id
- DELETE /datasources/{datasource_id}   - 删除验证 project_id
- POST   /datasources/test              - 测试验证 project_id

#### 3. app/api/notifications.py (通知渠道)
- POST   /notifications/                - 创建时设置 project_id
- GET    /notifications/                - 列表按 project_id 过滤
- GET    /notifications/{channel_id}    - 详情验证 project_id
- PUT    /notifications/{channel_id}    - 更新验证 project_id
- DELETE /notifications/{channel_id}    - 删除验证 project_id
- POST   /notifications/test            - 测试验证 project_id

#### 4. app/api/silence.py (静默规则)
- POST   /silence/                      - 创建时设置 project_id
- GET    /silence/                      - 列表按 project_id 过滤
- GET    /silence/{silence_id}          - 详情验证 project_id
- PUT    /silence/{silence_id}          - 更新验证 project_id
- DELETE /silence/{silence_id}          - 删除验证 project_id

### 不需要改造的 API
- app/api/users.py - 用户管理(租户级)
- app/api/auth.py - 认证(租户级)
- app/api/audit.py - 审计日志(租户级)
- app/api/settings.py - 系统设置(租户级)
- app/api/projects.py - 项目管理(已正确实现)

## 实施方案

### 阶段1: 数据库改造
1. 执行 SQL 脚本添加 project_id 字段
2. 更新 Model 添加 project_id 字段和关系
3. 验证数据完整性

### 阶段2: 工具类开发
创建 `app/core/project_access.py`:
- get_project_id_from_request() - 从请求获取并验证 project_id
- check_project_access() - 检查项目访问权限
- get_user_role_in_project() - 获取用户在项目中的角色

### 阶段3: API 改造
统一改造模式:
```python
from app.core.project_access import get_project_id_from_request

@router.post("/")
async def create_resource(
    data: ResourceCreate,
    project_id: int = Depends(get_project_id_from_request),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    new_resource = Resource(
        **data.dict(),
        tenant_id=current_user.tenant_id,
        project_id=project_id  # 添加项目隔离
    )
    # ...

@router.get("/")
async def list_resources(
    project_id: int = Depends(get_project_id_from_request),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Resource).where(
        and_(
            Resource.tenant_id == current_user.tenant_id,
            Resource.project_id == project_id  # 添加项目过滤
        )
    )
    # ...

@router.get("/{resource_id}")
async def get_resource(
    resource_id: int,
    project_id: int = Depends(get_project_id_from_request),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Resource).where(
        and_(
            Resource.id == resource_id,
            Resource.tenant_id == current_user.tenant_id,
            Resource.project_id == project_id  # 验证项目归属
        )
    )
    # ...
```

### 阶段4: 前端适配
前端 request.js 已实现自动注入 project_id:
```javascript
// 自动添加当前项目ID到请求参数
if (shouldAddProjectId && userStore.currentProject) {
  if (config.method === 'get') {
    config.params = {
      ...config.params,
      project_id: userStore.currentProject.id
    }
  } else {
    config.data = {
      ...config.data,
      project_id: userStore.currentProject.id
    }
  }
}
```

### 阶段5: 测试验证
1. 创建多个项目
2. 在不同项目创建资源
3. 切换项目验证数据隔离
4. 测试跨项目访问(应该被拒绝)

## 优先级
- P0: alert_rules, datasources (核心功能)
- P1: notifications, silence (告警相关)
- P2: alert_events, alert_event_history (数据展示)

## 注意事项
1. 所有 API 必须验证 project_id 归属
2. 创建资源时必须设置 project_id
3. 查询时必须添加 project_id 过滤条件
4. 更新/删除时必须验证 project_id
5. 避免直接使用 tenant_id 作为唯一隔离条件
