import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { login as loginApi, getUserInfo } from '@/api/auth'
import { getProjects } from '@/api/projects'

export const useUserStore = defineStore('user', () => {
  const token = ref(localStorage.getItem('token') || '')
  const userInfo = ref(null)
  const currentProject = ref(JSON.parse(localStorage.getItem('currentProject') || 'null'))
  const projects = ref([])

  // 权限列表
  const permissions = computed(() => {
    return userInfo.value?.permissions || []
  })

  // 是否是超级管理员
  const isSuperuser = computed(() => {
    return userInfo.value?.is_superuser || false
  })

  const login = async (username, password) => {
    const data = await loginApi(username, password)
    token.value = data.access_token
    localStorage.setItem('token', data.access_token)
    await fetchUserInfo()
  }

  const logout = () => {
    token.value = ''
    userInfo.value = null
    currentProject.value = null
    projects.value = []
    localStorage.removeItem('token')
    localStorage.removeItem('currentProject')
  }

  const fetchUserInfo = async () => {
    const data = await getUserInfo()
    userInfo.value = data
  }

  // 获取项目列表（延迟加载，避免在路由守卫中阻塞）
  const fetchProjects = async () => {
    try {
      const data = await getProjects()
      projects.value = data.projects || []
      
      // 如果没有当前项目，自动选择默认项目或第一个项目
      if (!currentProject.value && projects.value.length > 0) {
        const defaultProject = projects.value.find(p => p.is_default) || projects.value[0]
        setCurrentProject(defaultProject)
      }
    } catch (error) {
      console.error('获取项目列表失败:', error)
      // 即使失败也不抛出异常，避免阻塞页面加载
    }
  }

  // 切换当前项目
  const setCurrentProject = (project) => {
    currentProject.value = project
    localStorage.setItem('currentProject', JSON.stringify(project))
  }

  // 检查是否有指定权限
  const hasPermission = (permission) => {
    // 超级管理员拥有所有权限
    if (isSuperuser.value) return true
    // 检查权限列表
    return permissions.value.includes(permission)
  }

  // 检查是否有任意一个权限
  const hasAnyPermission = (permissionList) => {
    if (isSuperuser.value) return true
    return permissionList.some(p => permissions.value.includes(p))
  }

  // 检查是否拥有所有权限
  const hasAllPermissions = (permissionList) => {
    if (isSuperuser.value) return true
    return permissionList.every(p => permissions.value.includes(p))
  }

  // 检查当前项目角色权限
  const canCreate = () => {
    if (isSuperuser.value) return true
    const role = currentProject.value?.user_role
    return ['maintainer', 'admin'].includes(role)
  }

  const canUpdate = () => {
    if (isSuperuser.value) return true
    const role = currentProject.value?.user_role
    return ['maintainer', 'admin'].includes(role)
  }

  const canDelete = () => {
    if (isSuperuser.value) return true
    const role = currentProject.value?.user_role
    return role === 'admin'
  }

  const canManage = () => {
    if (isSuperuser.value) return true
    const role = currentProject.value?.user_role
    return role === 'admin'
  }

  return {
    token,
    userInfo,
    currentProject,
    projects,
    permissions,
    isSuperuser,
    login,
    logout,
    fetchUserInfo,
    fetchProjects,
    setCurrentProject,
    hasPermission,
    hasAnyPermission,
    hasAllPermissions,
    canCreate,
    canUpdate,
    canDelete,
    canManage
  }
})

