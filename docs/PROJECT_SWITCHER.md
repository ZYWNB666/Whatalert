# 项目切换功能说明

## 功能概述
在顶部导航栏添加了项目切换器，用户可以快速切换不同项目，实现项目间数据隔离。

## 使用位置
**顶部导航栏** - 用户头像左侧

## 功能特性

### 1. 项目切换器
- **图标显示**: 📁 文件夹图标 + 当前项目名称
- **下拉菜单**: 显示用户有权限访问的所有项目
- **默认项目标识**: ⭐ 星标标识默认项目
- **当前项目标识**: ✓ 对号标识当前选中的项目
- **快速切换**: 点击项目名称即可切换

### 2. 项目管理入口
下拉菜单底部提供"管理项目"链接，快速跳转到项目管理页面。

## 技术实现

### 前端改动

#### 1. Store扩展 (`web/src/stores/user.js`)
```javascript
// 新增状态
currentProject: ref(null)  // 当前选中的项目
projects: ref([])          // 用户可访问的项目列表

// 新增方法
fetchProjects()           // 获取项目列表
setCurrentProject()       // 切换当前项目
```

#### 2. 布局组件 (`web/src/layout/MainLayout.vue`)
```vue
<!-- 项目切换下拉菜单 -->
<el-dropdown @command="handleProjectChange">
  <div class="project-selector">
    <el-icon><Folder /></el-icon>
    <span>{{ currentProjectName }}</span>
  </div>
  <template #dropdown>
    <!-- 项目列表 -->
  </template>
</el-dropdown>
```

#### 3. 请求拦截器 (`web/src/api/request.js`)
自动在请求中添加 `project_id` 参数：
- GET请求: 添加到 `params`
- POST/PUT/DELETE请求: 添加到 `data`
- 排除路径: `/auth`, `/projects`, `/users`

### 数据流转

1. **用户登录** → 获取用户信息
2. **自动加载项目列表** → `fetchProjects()`
3. **自动选择默认项目** → 优先选择 `is_default=true` 的项目
4. **保存到localStorage** → 刷新页面后恢复选择
5. **切换项目** → 自动刷新页面以重新加载数据

## 用户体验

### 切换流程
1. 点击顶部的项目选择器
2. 在下拉列表中选择目标项目
3. 显示成功提示：`已切换到项目：XXX`
4. 页面自动刷新，加载新项目的数据

### 视觉设计
- **边框样式**: 淡灰色边框，hover时变为蓝色
- **激活状态**: 当前项目显示蓝色背景
- **图标标识**: 
  - ⭐ 默认项目
  - ✓ 当前选中
  - ⚙️ 管理入口

## API接口

### 获取项目列表
```http
GET /api/v1/projects
```

### 后端自动过滤
后端API会根据请求中的 `project_id` 参数自动过滤数据：
- 告警规则: 只返回当前项目的规则
- 数据源: 只返回当前项目的数据源
- 通知渠道: 只返回当前项目的渠道
- 静默规则: 只返回当前项目的规则

## 项目隔离说明

### 强隔离资源
以下资源严格按项目隔离：
- ✅ 告警规则 (alert_rule)
- ✅ 数据源 (datasource)
- ✅ 通知渠道 (notification_channel)
- ✅ 静默规则 (silence_rule)

### 共享资源
以下资源在租户级别共享：
- 用户 (user)
- 角色和权限 (role, permission)
- 审计日志 (audit_log)

## 注意事项

### 开发注意
1. **新增API时**: 需要在后端添加 `project_id` 过滤
2. **排除特殊接口**: 在 `request.js` 的 `excludePaths` 中添加
3. **跨项目操作**: 需要特殊权限验证

### 用户权限
- 用户只能看到自己有权限的项目
- 项目角色: owner, admin, member, viewer
- 不同角色有不同的操作权限

## 测试建议

### 功能测试
1. **项目切换**
   - 切换到不同项目
   - 验证数据隔离（告警规则、数据源等）
   - 验证页面刷新后项目选择保持

2. **权限测试**
   - 普通用户只能看到授权的项目
   - 超级管理员可以看到所有项目
   - 切换到无权限项目应被拒绝

3. **数据隔离测试**
   - 在项目A创建告警规则
   - 切换到项目B
   - 验证看不到项目A的规则

### UI测试
1. 顶部正确显示当前项目名称
2. 下拉菜单正确显示项目列表
3. 默认项目有星标
4. 当前项目有对号
5. hover效果正常
6. 切换成功有提示消息

## 后续优化建议

1. **性能优化**
   - 切换项目时不刷新页面，使用EventBus通知组件重新加载
   - 缓存各项目的数据，减少重复请求

2. **用户体验**
   - 添加项目搜索功能（项目多时）
   - 显示项目描述tooltip
   - 最近使用项目置顶

3. **功能增强**
   - 项目收藏功能
   - 项目颜色标识
   - 跨项目数据对比

## 相关文件

### 修改的文件
- `web/src/stores/user.js` - 添加项目状态管理
- `web/src/layout/MainLayout.vue` - 添加项目切换UI
- `web/src/api/request.js` - 添加项目ID自动注入

### 依赖的文件
- `web/src/api/projects.js` - 项目API
- `web/src/views/Projects/index.vue` - 项目管理页面

---

**更新时间**: 2025-11-17  
**功能版本**: v1.1.0
