python .\run_project_isolation.py# 项目切换功能 - 401错误排查指南

## 问题描述
访问 `http://localhost:8000/api/v1/projects/` 返回 401 Unauthorized

## 已修复的问题

### 1. 添加项目管理路由
在 `web/src/router/index.js` 中添加了项目管理页面路由：
```javascript
{
  path: 'projects',
  name: 'Projects',
  component: () => import('@/views/Projects/index.vue'),
  meta: { title: '项目管理', icon: 'Folder' }
}
```

### 2. 优化项目列表加载时机
- 从 `fetchUserInfo` 中移除自动调用 `fetchProjects`
- 改为在 `MainLayout.vue` 的 `onMounted` 中手动加载
- 避免在路由守卫中阻塞导航

### 3. 改进错误处理
在 `request.js` 中添加更详细的错误日志，帮助排查问题。

## 排查步骤

### 步骤1: 检查登录状态
打开浏览器开发者工具 (F12)，进入 Console：

```javascript
// 检查是否有token
localStorage.getItem('token')

// 检查store状态
import { useUserStore } from '@/stores/user'
const userStore = useUserStore()
console.log('Token:', userStore.token)
console.log('User Info:', userStore.userInfo)
```

**预期结果**: 应该能看到有效的token字符串

### 步骤2: 检查请求头
在 Network 标签中：
1. 刷新页面
2. 找到 `projects` 的请求
3. 查看 Request Headers

**应该包含**:
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**如果没有**: token没有正确设置或已过期

### 步骤3: 检查token是否有效
在 Console 中手动测试：

```javascript
fetch('http://localhost:8000/api/v1/auth/me', {
  headers: {
    'Authorization': 'Bearer ' + localStorage.getItem('token')
  }
})
.then(r => r.json())
.then(d => console.log('User Info:', d))
.catch(e => console.error('Error:', e))
```

**如果返回401**: token已过期或无效，需要重新登录

### 步骤4: 清除缓存重新登录

```javascript
// 在 Console 中执行
localStorage.clear()
location.href = '/login'
```

然后重新登录，观察是否正常。

## 常见问题

### Q1: 为什么会401？
**可能原因**:
1. Token过期（默认有效期配置在后端）
2. Token格式错误
3. 请求头中没有带token
4. 用户账号被禁用

### Q2: Token在哪里存储？
- 存储位置: `localStorage.token`
- 设置时机: 登录成功后
- 使用位置: 每次API请求的请求拦截器中

### Q3: 为什么有时能请求有时不能？
- 检查token是否在不同标签页之间同步
- 检查是否有多个窗口同时操作
- 查看控制台是否有CORS错误

## 解决方案

### 方案1: 增加Token有效期
编辑 `app/core/config.py`:
```python
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24小时
```

### 方案2: 实现Token自动刷新
在 `request.js` 中添加token刷新逻辑：
```javascript
// 401错误时尝试刷新token
if (error.response.status === 401) {
  // 刷新token逻辑
  // 重试原请求
}
```

### 方案3: 使用Token前验证
在发请求前检查token是否快过期：
```javascript
const isTokenValid = () => {
  const token = localStorage.getItem('token')
  if (!token) return false
  
  // 解析JWT，检查exp字段
  try {
    const payload = JSON.parse(atob(token.split('.')[1]))
    const exp = payload.exp * 1000
    return Date.now() < exp
  } catch {
    return false
  }
}
```

## 当前状态检查清单

- [ ] 用户已登录且token存在
- [ ] 请求头包含正确的Authorization
- [ ] 后端项目API已注册（/api/v1/projects）
- [ ] 前端路由已添加项目管理页面
- [ ] MainLayout正确加载项目列表
- [ ] 项目切换器在顶部导航栏显示

## 测试建议

### 测试1: 手动API测试
使用Postman或curl测试：

```bash
# 1. 先登录获取token
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin123"

# 2. 使用token请求项目列表
curl -X GET http://localhost:8000/api/v1/projects/ \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

### 测试2: 前端调试
在浏览器Console执行：

```javascript
// 1. 检查store
const userStore = useUserStore()
console.log('Store状态:', {
  hasToken: !!userStore.token,
  hasUserInfo: !!userStore.userInfo,
  projectCount: userStore.projects.length,
  currentProject: userStore.currentProject
})

// 2. 手动触发加载
await userStore.fetchProjects()
console.log('项目列表:', userStore.projects)

// 3. 检查请求拦截器
import axios from 'axios'
axios.interceptors.request.use(config => {
  console.log('请求配置:', config)
  return config
})
```

## 预期行为

### 正常流程
1. 用户登录 → 获取token → 存储到localStorage
2. 路由守卫检查token → 加载用户信息
3. MainLayout挂载 → 自动加载项目列表
4. 显示项目切换器 → 自动选择默认项目
5. 所有API请求自动带上project_id

### 项目切换流程
1. 点击项目选择器 → 显示项目列表
2. 选择目标项目 → 更新currentProject
3. 页面刷新 → 重新加载数据
4. 新数据只包含选中项目的内容

## 日志查看

### 后端日志
查看终端输出，找到401相关日志：
```
GET /api/v1/projects/ - 401 Unauthorized
```

### 前端日志
打开Console，查看：
- 红色错误信息
- Network标签中的请求详情
- 请求头和响应内容

---

**排查时间**: 2025-11-17  
**预计解决时间**: 5-10分钟

## 快速修复命令

如果以上都不行，执行以下命令重置：

```bash
# 1. 停止前端服务 (Ctrl+C)

# 2. 清理node_modules和重新安装
cd web
rm -rf node_modules
npm install

# 3. 重启前端
npm run dev

# 4. 清除浏览器所有缓存和Cookie
# 在浏览器中: F12 → Application → Clear storage → Clear site data

# 5. 重新登录测试
```
