import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '@/stores/user'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: { hideLayout: true }
  },
  {
    path: '/',
    component: () => import('@/layout/MainLayout.vue'),
    redirect: '/dashboard',
    children: [
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('@/views/Dashboard.vue'),
        meta: { title: '概览', icon: 'DataBoard' }
      },
      {
        path: 'alert-rules',
        name: 'AlertRules',
        component: () => import('@/views/AlertRules/index.vue'),
        meta: { title: '告警规则', icon: 'Bell', permission: 'alert_rule.read' }
      },
      {
        path: 'alert-rules/create',
        name: 'AlertRuleCreate',
        component: () => import('@/views/AlertRules/Create.vue'),
        meta: { title: '创建告警规则', hidden: true, permission: 'alert_rule.create' }
      },
      {
        path: 'alert-rules/edit/:id',
        name: 'AlertRuleEdit',
        component: () => import('@/views/AlertRules/Create.vue'),
        meta: { title: '编辑告警规则', hidden: true, permission: 'alert_rule.update' }
      },
      {
        path: 'current-alerts',
        name: 'CurrentAlerts',
        component: () => import('@/views/Alerts/CurrentAlerts.vue'),
        meta: { title: '当前告警', icon: 'Warning' }
      },
      {
        path: 'alert-history',
        name: 'AlertHistory',
        component: () => import('@/views/Alerts/AlertHistory.vue'),
        meta: { title: '历史告警', icon: 'Document' }
      },
      {
        path: 'silence',
        name: 'Silence',
        component: () => import('@/views/Silence/index.vue'),
        meta: { title: '静默规则', icon: 'Mute' }
      },
      {
        path: 'datasources',
        name: 'Datasources',
        component: () => import('@/views/Datasources/index.vue'),
        meta: { title: '数据源', icon: 'Connection', permission: 'datasource.read' }
      },
      {
        path: 'notifications',
        name: 'Notifications',
        component: () => import('@/views/Notifications/index.vue'),
        meta: { title: '通知渠道', icon: 'ChatDotRound', permission: 'notification.read' }
      },
      {
        path: 'projects',
        name: 'Projects',
        component: () => import('@/views/Projects/index.vue'),
        meta: { title: '项目管理', icon: 'Folder' }
      },
      {
        path: 'users',
        name: 'Users',
        component: () => import('@/views/Users/index.vue'),
        meta: { title: '用户管理', icon: 'User', permission: 'user.read' }
      },
      {
        path: 'settings',
        name: 'Settings',
        component: () => import('@/views/System/Settings.vue'),
        meta: { title: '系统设置', icon: 'Setting', permission: 'settings.read' }
      },
      {
        path: 'audit',
        name: 'Audit',
        component: () => import('@/views/Audit/index.vue'),
        meta: { title: '审计日志', icon: 'Tickets', requireSuperuser: true }
      },
      {
        path: 'profile',
        name: 'Profile',
        component: () => import('@/views/Profile/index.vue'),
        meta: { title: '个人设置', hidden: true }
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach(async (to, from, next) => {
  const userStore = useUserStore()
  
  // 检查是否从编辑/创建页面离开
  const isLeavingEditPage = (
    from.path.includes('/create') ||
    from.path.includes('/edit')
  ) && !to.path.includes('/create') && !to.path.includes('/edit')
  
  if (isLeavingEditPage) {
    // 动态导入 ElMessageBox 以避免循环依赖
    const { ElMessageBox } = await import('element-plus')
    
    try {
      await ElMessageBox.confirm(
        '当前页面有未保存的内容，确定要离开吗？',
        '提示',
        {
          confirmButtonText: '确定离开',
          cancelButtonText: '取消',
          type: 'warning',
          distinguishCancelAndClose: true
        }
      )
      // 用户确认离开，继续导航
    } catch (action) {
      // 用户取消或关闭对话框，阻止导航
      if (action === 'cancel' || action === 'close') {
        next(false)
        return
      }
    }
  }
  
  if (to.path !== '/login' && !userStore.token) {
    next('/login')
  } else if (to.path === '/login' && userStore.token) {
    next('/')
  } else if (to.path !== '/login' && userStore.token && !userStore.userInfo) {
    // 有token但没有用户信息，加载用户信息
    try {
      await userStore.fetchUserInfo()
      
      // 检查是否需要超级管理员权限
      if (to.meta?.requireSuperuser && !userStore.isSuperuser) {
        next('/')
        return
      }
      
      next()
    } catch (error) {
      // 加载失败，清除token并跳转到登录页
      userStore.logout()
      next('/login')
    }
  } else {
    // 已登录，检查权限
    if (to.meta?.requireSuperuser && !userStore.isSuperuser) {
      next('/')
      return
    }
    
    next()
  }
})

export default router

