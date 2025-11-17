import axios from 'axios'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/user'
import router from '@/router'

const service = axios.create({
  baseURL: '/api/v1',
  timeout: 30000
})

// 请求拦截器
service.interceptors.request.use(
  config => {
    const userStore = useUserStore()
    if (userStore.token) {
      config.headers['Authorization'] = `Bearer ${userStore.token}`
    }
    
    // 自动添加当前项目ID到请求参数（除了项目管理和登录相关接口）
    const excludePaths = ['/auth', '/projects', '/users']
    const shouldAddProjectId = !excludePaths.some(path => config.url.includes(path))
    
    if (shouldAddProjectId && userStore.currentProject) {
      // 对于GET/DELETE请求，添加到params
      if (config.method === 'get' || config.method === 'delete') {
        config.params = {
          ...config.params,
          project_id: userStore.currentProject.id
        }
      }
      // 对于POST/PUT请求，添加到data
      else if (config.data && typeof config.data === 'object') {
        config.data = {
          ...config.data,
          project_id: userStore.currentProject.id
        }
      }
    }
    
    return config
  },
  error => {
    console.error('请求错误:', error)
    return Promise.reject(error)
  }
)

// 响应拦截器
service.interceptors.response.use(
  response => {
    return response.data
  },
  error => {
    console.error('API请求失败:', error)
    
    if (error.response) {
      const status = error.response.status
      const detail = error.response.data?.detail || '请求失败'
      
      switch (status) {
        case 401:
          ElMessage.error('登录已过期，请重新登录')
          const userStore = useUserStore()
          userStore.logout()
          router.push('/login')
          break
        case 403:
          ElMessage.error('没有权限')
          break
        case 404:
          ElMessage.error('请求的资源不存在')
          break
        case 500:
          ElMessage.error('服务器错误')
          break
        default:
          ElMessage.error(detail)
      }
    } else if (error.request) {
      ElMessage.error('网络错误，请检查网络连接')
    } else {
      ElMessage.error('请求配置错误')
    }
    return Promise.reject(error)
  }
)

export default service

