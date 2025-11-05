# 权限系统说明

## 系统角色

系统预定义了三种角色：

### 1. 管理员 (admin)
- 拥有所有权限
- 可以管理用户、角色、数据源、告警规则、通知渠道等所有功能
- 可以查看审计日志和系统设置

### 2. 运维人员 (operator)
- 可以管理告警规则（创建、查看、更新、删除）
- 可以查看数据源（只读）
- 可以管理通知渠道（创建、查看、更新、删除）
- 可以查看审计日志

### 3. 查看者 (viewer)
- 只读权限
- 可以查看告警规则
- 可以查看数据源
- 可以查看通知渠道

## 权限列表

| 资源类型 | 权限代码 | 说明 |
|---------|----------|------|
| 告警规则 | alert_rule.read | 查看告警规则 |
| 告警规则 | alert_rule.create | 创建告警规则 |
| 告警规则 | alert_rule.update | 更新告警规则 |
| 告警规则 | alert_rule.delete | 删除告警规则 |
| 数据源 | datasource.read | 查看数据源 |
| 数据源 | datasource.create | 创建数据源 |
| 数据源 | datasource.update | 更新数据源 |
| 数据源 | datasource.delete | 删除数据源 |
| 通知渠道 | notification.read | 查看通知渠道 |
| 通知渠道 | notification.create | 创建通知渠道 |
| 通知渠道 | notification.update | 更新通知渠道 |
| 通知渠道 | notification.delete | 删除通知渠道 |
| 用户管理 | user.read | 查看用户 |
| 用户管理 | user.create | 创建用户 |
| 用户管理 | user.update | 更新用户 |
| 用户管理 | user.delete | 删除用户 |
| 系统设置 | settings.read | 查看系统设置 |
| 系统设置 | settings.update | 修改系统设置 |
| 审计日志 | audit.read | 查看审计日志 |

## 初始化权限

首次部署系统后，需要运行以下脚本初始化权限：

```bash
cd alert_system
python scripts/init_permissions.py
```

该脚本会：
1. 创建所有系统权限
2. 创建三种预定义角色
3. 为角色分配相应权限

## 分配角色给用户

### 为管理员用户分配admin角色

```bash
cd alert_system
python scripts/assign_admin_role.py
```

该脚本会自动为所有超级管理员（`is_superuser=True`）分配admin角色。

### 在Web界面分配角色

管理员可以在"用户管理"页面为用户分配角色：
1. 进入"用户管理"页面
2. 点击"编辑"按钮
3. 在角色下拉框中选择一个或多个角色
4. 点击"保存"

## 权限检查

### 后端权限检查

后端使用依赖注入的方式检查权限：

```python
from app.core.permissions import require_permission

@router.post("/")
async def create_resource(
    current_user: User = Depends(require_permission("resource", "create")),
    db: AsyncSession = Depends(get_db)
):
    # 只有拥有 resource.create 权限的用户才能访问
    pass
```

### 前端权限检查

前端使用用户 store 提供的权限检查方法：

```vue
<script setup>
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()

// 检查单个权限
const canCreate = userStore.hasPermission('alert_rule.create')

// 检查是否有任意一个权限
const canManage = userStore.hasAnyPermission([
  'alert_rule.update',
  'alert_rule.delete'
])
</script>

<template>
  <el-button v-if="canCreate" @click="handleCreate">创建</el-button>
</template>
```

## 注意事项

1. **超级管理员**：标记为 `is_superuser=True` 的用户拥有所有权限，无需分配角色
2. **多角色**：一个用户可以拥有多个角色，权限会合并
3. **菜单过滤**：前端会根据用户权限自动过滤侧边栏菜单
4. **路由保护**：后端API会检查权限，前端无权限用户无法调用接口

## 自定义权限

如果需要添加新的权限，请修改 `scripts/init_permissions.py` 中的 `PERMISSIONS` 列表，然后重新运行初始化脚本。

