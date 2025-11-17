<template>
  <el-container class="main-layout">
    <el-aside width="240px" class="sidebar">
      <div class="logo">
        <el-icon class="logo-icon"><Bell /></el-icon>
        <span class="logo-text">监控告警系统</span>
      </div>
      <el-menu
        :default-active="activeMenu"
        class="el-menu-vertical"
        :router="true"
      >
        <template v-for="route in menuRoutes" :key="route.path">
          <el-menu-item 
            v-if="!route.meta?.hidden"
            :index="route.path"
          >
            <el-icon v-if="route.meta?.icon">
              <component :is="route.meta.icon" />
            </el-icon>
            <span>{{ route.meta?.title }}</span>
          </el-menu-item>
        </template>
      </el-menu>
    </el-aside>
    
    <el-container>
      <el-header class="header">
        <div class="header-left">
          <el-breadcrumb separator="/">
            <el-breadcrumb-item>{{ currentTitle }}</el-breadcrumb-item>
          </el-breadcrumb>
        </div>
        <div class="header-right">
          <!-- 项目切换器 -->
          <el-dropdown @command="handleProjectChange" class="project-dropdown">
            <div class="project-selector">
              <el-icon><Folder /></el-icon>
              <span>{{ currentProjectName }}</span>
              <el-icon class="arrow"><ArrowDown /></el-icon>
            </div>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item 
                  v-for="project in userStore.projects" 
                  :key="project.id"
                  :command="project"
                  :class="{ 'is-active': project.id === userStore.currentProject?.id }"
                >
                  <el-icon v-if="project.is_default"><Star /></el-icon>
                  <span>{{ project.name }}</span>
                  <el-icon v-if="project.id === userStore.currentProject?.id" class="check-icon">
                    <Check />
                  </el-icon>
                </el-dropdown-item>
                <el-dropdown-item divided @click="handleManageProjects">
                  <el-icon><Setting /></el-icon>
                  管理项目
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>

          <!-- 用户菜单 -->
          <el-dropdown>
            <div class="user-info">
              <el-icon><User /></el-icon>
              <span>{{ userStore.userInfo?.email || '用户' }}</span>
            </div>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item @click="handleProfile">
                  <el-icon><Setting /></el-icon>
                  个人设置
                </el-dropdown-item>
                <el-dropdown-item divided @click="handleLogout">
                  <el-icon><SwitchButton /></el-icon>
                  退出登录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>
      
      <el-main class="main-content">
        <router-view v-slot="{ Component }">
          <keep-alive>
            <component :is="Component" />
          </keep-alive>
        </router-view>
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { ElMessage, ElMessageBox } from 'element-plus'
import { onMounted } from 'vue'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

// 组件挂载后加载项目列表
onMounted(async () => {
  if (userStore.token && !userStore.projects.length) {
    await userStore.fetchProjects()
  }
})

const menuRoutes = computed(() => {
  const allRoutes = router.getRoutes()
    .find(r => r.path === '/')
    ?.children || []
  
  // 根据用户权限过滤菜单
  return allRoutes.filter(route => {
    // 检查是否需要超级管理员权限
    if (route.meta?.requireSuperuser) {
      return userStore.isSuperuser
    }
    
    // 没有权限要求的路由，所有人都可以访问
    if (!route.meta?.permission) return true
    
    // 检查用户是否有权限
    return userStore.hasPermission(route.meta.permission)
  })
})

const activeMenu = computed(() => {
  return '/' + route.path.split('/')[1]
})

const currentTitle = computed(() => {
  return route.meta?.title || '概览'
})

const currentProjectName = computed(() => {
  return userStore.currentProject?.name || '选择项目'
})

const handleProjectChange = (project) => {
  userStore.setCurrentProject(project)
  ElMessage.success(`已切换到项目：${project.name}`)
  // 刷新当前页面数据
  window.location.reload()
}

const handleManageProjects = () => {
  router.push('/projects')
}

const handleProfile = () => {
  router.push('/profile')
}

const handleLogout = async () => {
  try {
    await ElMessageBox.confirm('确定要退出登录吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    userStore.logout()
    router.push('/login')
    ElMessage.success('已退出登录')
  } catch (e) {
    // 取消
  }
}
</script>

<style scoped lang="scss">
.main-layout {
  height: 100vh;
}

.sidebar {
  background: #001529;
  color: #fff;
  
  .logo {
    height: 60px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 18px;
    font-weight: bold;
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
    
    .logo-icon {
      font-size: 24px;
      margin-right: 8px;
    }
  }
  
  .el-menu {
    border-right: none;
    background: #001529;
    
    :deep(.el-menu-item) {
      color: rgba(255, 255, 255, 0.65);
      
      &:hover {
        color: #fff;
        background: rgba(255, 255, 255, 0.08);
      }
      
      &.is-active {
        color: #fff;
        background: #1890ff;
      }
    }
  }
}

.header {
  background: #fff;
  border-bottom: 1px solid #f0f0f0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  
  .header-left {
    .el-breadcrumb {
      font-size: 16px;
    }
  }
  
  .header-right {
    display: flex;
    align-items: center;
    gap: 16px;
    
    .project-dropdown {
      .project-selector {
        display: flex;
        align-items: center;
        gap: 6px;
        cursor: pointer;
        padding: 6px 12px;
        border-radius: 4px;
        border: 1px solid #d9d9d9;
        background: #fff;
        transition: all 0.3s;
        
        &:hover {
          border-color: #1890ff;
          color: #1890ff;
        }
        
        .arrow {
          font-size: 12px;
          transition: transform 0.3s;
        }
      }
    }
    
    .user-info {
      display: flex;
      align-items: center;
      gap: 8px;
      cursor: pointer;
      padding: 8px 12px;
      border-radius: 4px;
      
      &:hover {
        background: #f5f7fa;
      }
    }
  }
}

:deep(.el-dropdown-menu__item) {
  &.is-active {
    background: #e6f7ff;
    color: #1890ff;
  }
  
  .check-icon {
    margin-left: auto;
    color: #52c41a;
  }
}

.main-content {
  background: #f5f7fa;
  padding: 20px;
}
</style>

