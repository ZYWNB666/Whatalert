/**
 * 前端工具函数库
 * 
 * 提供常用的工具函数，包括：
 * - 日期格式化
 * - 数据验证
 * - 防抖节流
 * - 本地存储
 * - 数据处理
 */

import dayjs from 'dayjs'

/**
 * 日期格式化
 * @param {Date|string|number} date - 日期
 * @param {string} format - 格式化模板
 * @returns {string} 格式化后的日期字符串
 */
export function formatDate(date, format = 'YYYY-MM-DD HH:mm:ss') {
  if (!date) return ''
  return dayjs(date).format(format)
}

/**
 * 相对时间
 * @param {Date|string|number} date - 日期
 * @returns {string} 相对时间描述
 */
export function timeAgo(date) {
  if (!date) return ''
  
  const now = dayjs()
  const target = dayjs(date)
  const diff = now.diff(target, 'second')
  
  if (diff < 60) return '刚刚'
  if (diff < 3600) return `${Math.floor(diff / 60)} 分钟前`
  if (diff < 86400) return `${Math.floor(diff / 3600)} 小时前`
  if (diff < 2592000) return `${Math.floor(diff / 86400)} 天前`
  
  return formatDate(date, 'YYYY-MM-DD')
}

/**
 * 持续时间格式化
 * @param {number} seconds - 秒数
 * @returns {string} 格式化后的持续时间
 */
export function formatDuration(seconds) {
  if (!seconds || seconds < 0) return '0秒'
  
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  const secs = seconds % 60
  
  const parts = []
  if (hours > 0) parts.push(`${hours}小时`)
  if (minutes > 0) parts.push(`${minutes}分钟`)
  if (secs > 0 || parts.length === 0) parts.push(`${secs}秒`)
  
  return parts.join('')
}

/**
 * 防抖函数
 * @param {Function} func - 要防抖的函数
 * @param {number} wait - 等待时间（毫秒）
 * @returns {Function} 防抖后的函数
 */
export function debounce(func, wait = 300) {
  let timeout
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout)
      func(...args)
    }
    clearTimeout(timeout)
    timeout = setTimeout(later, wait)
  }
}

/**
 * 节流函数
 * @param {Function} func - 要节流的函数
 * @param {number} limit - 时间限制（毫秒）
 * @returns {Function} 节流后的函数
 */
export function throttle(func, limit = 300) {
  let inThrottle
  return function executedFunction(...args) {
    if (!inThrottle) {
      func(...args)
      inThrottle = true
      setTimeout(() => (inThrottle = false), limit)
    }
  }
}

/**
 * 深拷贝
 * @param {any} obj - 要拷贝的对象
 * @returns {any} 拷贝后的对象
 */
export function deepClone(obj) {
  if (obj === null || typeof obj !== 'object') return obj
  if (obj instanceof Date) return new Date(obj.getTime())
  if (obj instanceof Array) return obj.map(item => deepClone(item))
  if (obj instanceof Object) {
    const clonedObj = {}
    for (const key in obj) {
      if (obj.hasOwnProperty(key)) {
        clonedObj[key] = deepClone(obj[key])
      }
    }
    return clonedObj
  }
}

/**
 * 本地存储封装
 */
export const storage = {
  /**
   * 设置存储
   * @param {string} key - 键
   * @param {any} value - 值
   * @param {number} expire - 过期时间（秒），0 表示永不过期
   */
  set(key, value, expire = 0) {
    const data = {
      value,
      expire: expire > 0 ? Date.now() + expire * 1000 : 0
    }
    localStorage.setItem(key, JSON.stringify(data))
  },

  /**
   * 获取存储
   * @param {string} key - 键
   * @returns {any} 值
   */
  get(key) {
    const item = localStorage.getItem(key)
    if (!item) return null

    try {
      const data = JSON.parse(item)
      
      // 检查是否过期
      if (data.expire && data.expire < Date.now()) {
        localStorage.removeItem(key)
        return null
      }
      
      return data.value
    } catch (e) {
      return null
    }
  },

  /**
   * 删除存储
   * @param {string} key - 键
   */
  remove(key) {
    localStorage.removeItem(key)
  },

  /**
   * 清空存储
   */
  clear() {
    localStorage.clear()
  }
}

/**
 * 数字格式化
 * @param {number} num - 数字
 * @param {number} precision - 精度
 * @returns {string} 格式化后的数字
 */
export function formatNumber(num, precision = 2) {
  if (num === null || num === undefined) return '0'
  
  const absNum = Math.abs(num)
  
  if (absNum >= 1e9) {
    return (num / 1e9).toFixed(precision) + 'B'
  }
  if (absNum >= 1e6) {
    return (num / 1e6).toFixed(precision) + 'M'
  }
  if (absNum >= 1e3) {
    return (num / 1e3).toFixed(precision) + 'K'
  }
  
  return num.toFixed(precision)
}

/**
 * 文件大小格式化
 * @param {number} bytes - 字节数
 * @returns {string} 格式化后的文件大小
 */
export function formatFileSize(bytes) {
  if (bytes === 0) return '0 B'
  
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  
  return (bytes / Math.pow(k, i)).toFixed(2) + ' ' + sizes[i]
}

/**
 * URL 参数解析
 * @param {string} url - URL 字符串
 * @returns {Object} 参数对象
 */
export function parseQuery(url = window.location.href) {
  const query = {}
  const queryString = url.split('?')[1]
  
  if (!queryString) return query
  
  queryString.split('&').forEach(param => {
    const [key, value] = param.split('=')
    query[decodeURIComponent(key)] = decodeURIComponent(value || '')
  })
  
  return query
}

/**
 * 对象转 URL 参数
 * @param {Object} obj - 参数对象
 * @returns {string} URL 参数字符串
 */
export function stringifyQuery(obj) {
  if (!obj || typeof obj !== 'object') return ''
  
  return Object.keys(obj)
    .filter(key => obj[key] !== null && obj[key] !== undefined)
    .map(key => `${encodeURIComponent(key)}=${encodeURIComponent(obj[key])}`)
    .join('&')
}

/**
 * 生成唯一 ID
 * @returns {string} 唯一 ID
 */
export function generateId() {
  return Date.now().toString(36) + Math.random().toString(36).substr(2)
}

/**
 * 数组去重
 * @param {Array} arr - 数组
 * @param {string} key - 对象数组的唯一键
 * @returns {Array} 去重后的数组
 */
export function unique(arr, key) {
  if (!Array.isArray(arr)) return []
  
  if (key) {
    const seen = new Set()
    return arr.filter(item => {
      const k = item[key]
      if (seen.has(k)) return false
      seen.add(k)
      return true
    })
  }
  
  return [...new Set(arr)]
}

/**
 * 数组分组
 * @param {Array} arr - 数组
 * @param {string|Function} key - 分组键或函数
 * @returns {Object} 分组后的对象
 */
export function groupBy(arr, key) {
  if (!Array.isArray(arr)) return {}
  
  return arr.reduce((result, item) => {
    const groupKey = typeof key === 'function' ? key(item) : item[key]
    if (!result[groupKey]) {
      result[groupKey] = []
    }
    result[groupKey].push(item)
    return result
  }, {})
}

/**
 * 下载文件
 * @param {Blob|string} data - 文件数据或 URL
 * @param {string} filename - 文件名
 */
export function downloadFile(data, filename) {
  const url = data instanceof Blob ? URL.createObjectURL(data) : data
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  
  if (data instanceof Blob) {
    URL.revokeObjectURL(url)
  }
}

/**
 * 复制到剪贴板
 * @param {string} text - 要复制的文本
 * @returns {Promise<boolean>} 是否成功
 */
export async function copyToClipboard(text) {
  try {
    if (navigator.clipboard) {
      await navigator.clipboard.writeText(text)
      return true
    }
    
    // 降级方案
    const textarea = document.createElement('textarea')
    textarea.value = text
    textarea.style.position = 'fixed'
    textarea.style.opacity = '0'
    document.body.appendChild(textarea)
    textarea.select()
    const success = document.execCommand('copy')
    document.body.removeChild(textarea)
    return success
  } catch (e) {
    console.error('复制失败:', e)
    return false
  }
}

/**
 * 验证邮箱
 * @param {string} email - 邮箱地址
 * @returns {boolean} 是否有效
 */
export function isValidEmail(email) {
  const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  return re.test(email)
}

/**
 * 验证手机号
 * @param {string} phone - 手机号
 * @returns {boolean} 是否有效
 */
export function isValidPhone(phone) {
  const re = /^1[3-9]\d{9}$/
  return re.test(phone)
}

/**
 * 验证 URL
 * @param {string} url - URL 地址
 * @returns {boolean} 是否有效
 */
export function isValidUrl(url) {
  try {
    new URL(url)
    return true
  } catch (e) {
    return false
  }
}

/**
 * 高亮搜索关键词
 * @param {string} text - 原文本
 * @param {string} keyword - 关键词
 * @returns {string} 高亮后的 HTML
 */
export function highlightKeyword(text, keyword) {
  if (!keyword) return text
  
  const reg = new RegExp(keyword, 'gi')
  return text.replace(reg, match => `<mark>${match}</mark>`)
}

/**
 * 等待指定时间
 * @param {number} ms - 毫秒数
 * @returns {Promise}
 */
export function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms))
}

/**
 * 重试函数
 * @param {Function} fn - 要重试的函数
 * @param {number} retries - 重试次数
 * @param {number} delay - 重试延迟（毫秒）
 * @returns {Promise}
 */
export async function retry(fn, retries = 3, delay = 1000) {
  try {
    return await fn()
  } catch (error) {
    if (retries <= 0) throw error
    await sleep(delay)
    return retry(fn, retries - 1, delay)
  }
}