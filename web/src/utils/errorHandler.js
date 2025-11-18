/**
 * 前端错误处理工具
 * 
 * 提供统一的错误处理、日志记录和用户提示功能
 */
import { ElMessage, ElNotification } from 'element-plus'

/**
 * 错误级别
 */
export const ErrorLevel = {
  INFO: 'info',
  WARNING: 'warning',
  ERROR: 'error',
  CRITICAL: 'critical'
}

/**
 * 错误处理器类
 */
class ErrorHandler {
  constructor() {
    this.errorLog = []
    this.maxLogSize = 100
  }

  /**
   * 记录错误
   * @param {Error} error - 错误对象
   * @param {string} level - 错误级别
   * @param {Object} context - 上下文信息
   */
  log(error, level = ErrorLevel.ERROR, context = {}) {
    const errorRecord = {
      timestamp: new Date().toISOString(),
      level,
      message: error.message || String(error),
      stack: error.stack,
      context,
      userAgent: navigator.userAgent,
      url: window.location.href
    }

    this.errorLog.push(errorRecord)

    // 限制日志大小
    if (this.errorLog.length > this.maxLogSize) {
      this.errorLog.shift()
    }

    // 开发环境下输出到控制台
    if (import.meta.env.DEV) {
      console.group(`🔴 ${level.toUpperCase()} Error`)
      console.error('Message:', error.message)
      console.error('Context:', context)
      console.error('Stack:', error.stack)
      console.groupEnd()
    }

    // 生产环境可以发送到错误追踪服务（如 Sentry）
    if (import.meta.env.PROD && level === ErrorLevel.CRITICAL) {
      this.reportToService(errorRecord)
    }
  }

  /**
   * 上报错误到服务端
   * @param {Object} errorRecord - 错误记录
   */
  reportToService(errorRecord) {
    // TODO: 集成 Sentry 或其他错误追踪服务
    console.log('Report error to service:', errorRecord)
  }

  /**
   * 获取错误日志
   * @returns {Array} 错误日志列表
   */
  getErrorLog() {
    return [...this.errorLog]
  }

  /**
   * 清空错误日志
   */
  clearErrorLog() {
    this.errorLog = []
  }

  /**
   * 处理异步错误
   * @param {Promise} promise - Promise 对象
   * @param {string} errorMessage - 错误提示消息
   * @returns {Promise}
   */
  async handleAsync(promise, errorMessage = '操作失败') {
    try {
      return await promise
    } catch (error) {
      this.log(error, ErrorLevel.ERROR, { customMessage: errorMessage })
      ElMessage.error(errorMessage)
      throw error
    }
  }

  /**
   * 包装函数以自动处理错误
   * @param {Function} fn - 要包装的函数
   * @param {string} errorMessage - 错误提示消息
   * @returns {Function}
   */
  wrapFunction(fn, errorMessage = '操作失败') {
    return async (...args) => {
      try {
        return await fn(...args)
      } catch (error) {
        this.log(error, ErrorLevel.ERROR, { 
          function: fn.name,
          arguments: args 
        })
        ElMessage.error(errorMessage)
        throw error
      }
    }
  }
}

// 创建单例
const errorHandler = new ErrorHandler()

/**
 * 全局错误处理器
 */
export function setupGlobalErrorHandler() {
  // 捕获未处理的 Promise 错误
  window.addEventListener('unhandledrejection', (event) => {
    errorHandler.log(
      new Error(event.reason),
      ErrorLevel.ERROR,
      { type: 'unhandledrejection' }
    )
    event.preventDefault()
  })

  // 捕获全局错误
  window.addEventListener('error', (event) => {
    errorHandler.log(
      event.error || new Error(event.message),
      ErrorLevel.ERROR,
      { 
        type: 'global',
        filename: event.filename,
        lineno: event.lineno,
        colno: event.colno
      }
    )
  })

  // Vue 错误处理器会在 main.js 中设置
}

/**
 * 显示成功消息
 * @param {string} message - 消息内容
 */
export function showSuccess(message) {
  ElMessage.success(message)
}

/**
 * 显示警告消息
 * @param {string} message - 消息内容
 */
export function showWarning(message) {
  ElMessage.warning(message)
}

/**
 * 显示错误消息
 * @param {string} message - 消息内容
 */
export function showError(message) {
  ElMessage.error(message)
}

/**
 * 显示通知
 * @param {Object} options - 通知选项
 */
export function showNotification(options) {
  ElNotification(options)
}

export default errorHandler