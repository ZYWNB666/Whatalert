/**
 * Axios 请求封装
 *
 * 提供统一的 HTTP 请求接口，包括：
 * - 自动添加认证 Token
 * - 自动添加项目 ID
 * - 统一的错误处理
 * - 请求/响应拦截
 */
import axios from 'axios'
import { ElMessage, ElNotification } from 'element-plus'
import { useUserStore } from '@/stores/user'
import router from '@/router'

// 错误码映射
const ERROR_MESSAGES = {
  RESOURCE_NOT_FOUND: '资源不存在',
  PERMISSION_DENIED: '权限不足',
  VALIDATION_ERROR: '数据验证失败',
  DATABASE_ERROR: '数据库操作失败',
  EXTERNAL_SERVICE_ERROR: '外部服务错误',
  CONFIGURATION_ERROR: '配置错误',
  RATE_LIMIT_EXCEEDED: '请求过于频繁，请稍后再试',
  DUPLICATE_RESOURCE: '资源已存在',
  TENANT_ISOLATION_VIOLATION: '租户隔离违规',
  INTERNAL_SERVER_ERROR: '服务器内部错误'
}

/**
 * 创建 Axios 实例
 */
const service = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

/**
 * 请求拦截器
 */
service.interceptors.request.use(
  config => {
    const userStore = useUserStore()
    
    // 添加认证 Token
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
    console.error('请求配置错误:', error)
    ElMessage.error('请求配置错误')
    return Promise.reject(error)
  }
)

/**
 * 响应拦截器
 */
service.interceptors.response.use(
  response => {
    return response.data
  },
  error => {
    handleError(error)
    return Promise.reject(error)
  }
)

/**
 * 统一错误处理
 * @param {Error} error - 错误对象
 */
function handleError(error) {
  console.error('API 请求失败:', error)
  
  if (error.response) {
    const { status, data } = error.response
    
    // 处理后端返回的标准错误格式
    if (data?.error) {
      handleBackendError(status, data.error)
    } else {
      // 处理旧格式或非标准错误
      handleHttpError(status, data?.detail || '请求失败')
    }
  } else if (error.request) {
    // 请求已发送但没有收到响应
    ElNotification({
      title: '网络错误',
      message: '无法连接到服务器，请检查网络连接',
      type: 'error',
      duration: 5000
    })
  } else {
    // 请求配置错误
    ElMessage.error('请求配置错误')
  }
}

/**
 * 处理后端标准错误格式
 * @param {number} status - HTTP 状态码
 * @param {Object} error - 错误对象 {code, message, details}
 */
function handleBackendError(status, error) {
  const { code, message, details } = error
  
  // 特殊处理认证错误
  if (status === 401) {
    ElMessage.error('登录已过期，请重新登录')
    const userStore = useUserStore()
    userStore.logout()
    router.push('/login')
    return
  }
  
  // 使用错误码映射或后端返回的消息
  const errorMessage = ERROR_MESSAGES[code] || message || '操作失败'
  
  // 根据错误类型选择通知方式
  if (status >= 500) {
    // 服务器错误使用通知
    ElNotification({
      title: '服务器错误',
      message: errorMessage,
      type: 'error',
      duration: 5000
    })
  } else if (code === 'VALIDATION_ERROR' && details?.field) {
    // 验证错误显示详细信息
    ElMessage.error(`${details.field}: ${details.validation_message || errorMessage}`)
  } else {
    // 其他错误使用消息提示
    ElMessage.error(errorMessage)
  }
  
  // 开发环境下输出详细错误信息
  if (import.meta.env.DEV) {
    console.group('🔴 API Error Details')
    console.log('Status:', status)
    console.log('Code:', code)
    console.log('Message:', message)
    console.log('Details:', details)
    console.groupEnd()
  }
}

/**
 * 处理 HTTP 状态码错误（兼容旧格式）
 * @param {number} status - HTTP 状态码
 * @param {string} detail - 错误详情
 */
function handleHttpError(status, detail) {
  switch (status) {
    case 401:
      ElMessage.error('登录已过期，请重新登录')
      const userStore = useUserStore()
      userStore.logout()
      router.push('/login')
      break
    case 403:
      ElMessage.error('没有权限执行此操作')
      break
    case 404:
      ElMessage.error('请求的资源不存在')
      break
    case 422:
      ElMessage.error(detail || '数据验证失败')
      break
    case 429:
      ElMessage.error('请求过于频繁，请稍后再试')
      break
    case 500:
      ElNotification({
        title: '服务器错误',
        message: '服务器内部错误，请稍后重试',
        type: 'error',
        duration: 5000
      })
      break
    case 503:
      ElNotification({
        title: '服务不可用',
        message: '服务暂时不可用，请稍后重试',
        type: 'error',
        duration: 5000
      })
      break
    default:
      ElMessage.error(detail || '请求失败')
  }
}

/**
 * 导出请求实例
 */
export default service

/**
 * 导出便捷方法
 */
export const request = {
  get: (url, params, config) => service.get(url, { params, ...config }),
  post: (url, data, config) => service.post(url, data, config),
  put: (url, data, config) => service.put(url, data, config),
  delete: (url, params, config) => service.delete(url, { params, ...config }),
  patch: (url, data, config) => service.patch(url, data, config)
}

