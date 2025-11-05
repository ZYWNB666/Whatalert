import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { login as loginApi, getUserInfo } from '@/api/auth'

export const useUserStore = defineStore('user', () => {
  const token = ref(localStorage.getItem('token') || '')
  const userInfo = ref(null)

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
    localStorage.removeItem('token')
  }

  const fetchUserInfo = async () => {
    const data = await getUserInfo()
    userInfo.value = data
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

  return {
    token,
    userInfo,
    permissions,
    isSuperuser,
    login,
    logout,
    fetchUserInfo,
    hasPermission,
    hasAnyPermission,
    hasAllPermissions
  }
})

