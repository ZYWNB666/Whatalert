/**
 * 性能监控工具
 * 
 * 提供前端性能监控功能，包括：
 * - 页面加载性能
 * - API 请求性能
 * - 组件渲染性能
 * - 资源加载性能
 */

/**
 * 性能指标收集器
 */
class PerformanceMonitor {
  constructor() {
    this.metrics = []
    this.apiMetrics = []
    this.componentMetrics = []
  }

  /**
   * 收集页面加载性能
   */
  collectPagePerformance() {
    if (!window.performance || !window.performance.timing) {
      console.warn('Performance API not supported')
      return null
    }

    const timing = window.performance.timing
    const navigation = window.performance.navigation

    const metrics = {
      // DNS 查询耗时
      dns: timing.domainLookupEnd - timing.domainLookupStart,
      // TCP 连接耗时
      tcp: timing.connectEnd - timing.connectStart,
      // SSL 安全连接耗时
      ssl: timing.secureConnectionStart ? timing.connectEnd - timing.secureConnectionStart : 0,
      // 网络请求耗时
      request: timing.responseStart - timing.requestStart,
      // 数据传输耗时
      response: timing.responseEnd - timing.responseStart,
      // DOM 解析耗时
      domParse: timing.domInteractive - timing.domLoading,
      // 资源加载耗时
      resourceLoad: timing.loadEventStart - timing.domContentLoadedEventEnd,
      // 首次渲染时间
      firstPaint: this.getFirstPaint(),
      // 首次内容绘制
      firstContentfulPaint: this.getFirstContentfulPaint(),
      // DOM Ready 时间
      domReady: timing.domContentLoadedEventEnd - timing.navigationStart,
      // 页面完全加载时间
      loadComplete: timing.loadEventEnd - timing.navigationStart,
      // 页面类型
      navigationType: this.getNavigationType(navigation.type)
    }

    this.metrics.push({
      type: 'page',
      timestamp: Date.now(),
      metrics
    })

    return metrics
  }

  /**
   * 获取首次绘制时间
   */
  getFirstPaint() {
    if (!window.performance || !window.performance.getEntriesByType) {
      return 0
    }

    const paintEntries = window.performance.getEntriesByType('paint')
    const firstPaint = paintEntries.find(entry => entry.name === 'first-paint')
    return firstPaint ? Math.round(firstPaint.startTime) : 0
  }

  /**
   * 获取首次内容绘制时间
   */
  getFirstContentfulPaint() {
    if (!window.performance || !window.performance.getEntriesByType) {
      return 0
    }

    const paintEntries = window.performance.getEntriesByType('paint')
    const fcp = paintEntries.find(entry => entry.name === 'first-contentful-paint')
    return fcp ? Math.round(fcp.startTime) : 0
  }

  /**
   * 获取导航类型
   */
  getNavigationType(type) {
    const types = {
      0: 'navigate',
      1: 'reload',
      2: 'back_forward',
      255: 'reserved'
    }
    return types[type] || 'unknown'
  }

  /**
   * 记录 API 请求性能
   * @param {string} url - 请求 URL
   * @param {number} duration - 请求耗时（毫秒）
   * @param {number} status - HTTP 状态码
   * @param {number} size - 响应大小（字节）
   */
  recordApiMetric(url, duration, status, size = 0) {
    const metric = {
      url,
      duration,
      status,
      size,
      timestamp: Date.now()
    }

    this.apiMetrics.push(metric)

    // 只保留最近 100 条记录
    if (this.apiMetrics.length > 100) {
      this.apiMetrics.shift()
    }

    // 开发环境输出慢请求警告
    if (import.meta.env.DEV && duration > 3000) {
      console.warn(`⚠️ Slow API request: ${url} took ${duration}ms`)
    }

    return metric
  }

  /**
   * 记录组件渲染性能
   * @param {string} componentName - 组件名称
   * @param {number} duration - 渲染耗时（毫秒）
   */
  recordComponentMetric(componentName, duration) {
    const metric = {
      component: componentName,
      duration,
      timestamp: Date.now()
    }

    this.componentMetrics.push(metric)

    // 只保留最近 50 条记录
    if (this.componentMetrics.length > 50) {
      this.componentMetrics.shift()
    }

    // 开发环境输出慢渲染警告
    if (import.meta.env.DEV && duration > 100) {
      console.warn(`⚠️ Slow component render: ${componentName} took ${duration}ms`)
    }

    return metric
  }

  /**
   * 获取资源加载性能
   */
  getResourcePerformance() {
    if (!window.performance || !window.performance.getEntriesByType) {
      return []
    }

    const resources = window.performance.getEntriesByType('resource')
    
    return resources.map(resource => ({
      name: resource.name,
      type: resource.initiatorType,
      duration: Math.round(resource.duration),
      size: resource.transferSize || 0,
      cached: resource.transferSize === 0 && resource.decodedBodySize > 0
    }))
  }

  /**
   * 获取性能报告
   */
  getPerformanceReport() {
    const apiStats = this.getApiStats()
    const componentStats = this.getComponentStats()
    const resourceStats = this.getResourceStats()

    return {
      page: this.metrics[this.metrics.length - 1]?.metrics || null,
      api: apiStats,
      components: componentStats,
      resources: resourceStats,
      timestamp: Date.now()
    }
  }

  /**
   * 获取 API 统计
   */
  getApiStats() {
    if (this.apiMetrics.length === 0) return null

    const durations = this.apiMetrics.map(m => m.duration)
    const sizes = this.apiMetrics.map(m => m.size)

    return {
      count: this.apiMetrics.length,
      avgDuration: Math.round(durations.reduce((a, b) => a + b, 0) / durations.length),
      maxDuration: Math.max(...durations),
      minDuration: Math.min(...durations),
      totalSize: sizes.reduce((a, b) => a + b, 0),
      slowRequests: this.apiMetrics.filter(m => m.duration > 3000).length,
      errorRequests: this.apiMetrics.filter(m => m.status >= 400).length
    }
  }

  /**
   * 获取组件统计
   */
  getComponentStats() {
    if (this.componentMetrics.length === 0) return null

    const durations = this.componentMetrics.map(m => m.duration)

    return {
      count: this.componentMetrics.length,
      avgDuration: Math.round(durations.reduce((a, b) => a + b, 0) / durations.length),
      maxDuration: Math.max(...durations),
      slowRenders: this.componentMetrics.filter(m => m.duration > 100).length
    }
  }

  /**
   * 获取资源统计
   */
  getResourceStats() {
    const resources = this.getResourcePerformance()
    if (resources.length === 0) return null

    const byType = resources.reduce((acc, resource) => {
      if (!acc[resource.type]) {
        acc[resource.type] = { count: 0, size: 0, duration: 0 }
      }
      acc[resource.type].count++
      acc[resource.type].size += resource.size
      acc[resource.type].duration += resource.duration
      return acc
    }, {})

    return {
      total: resources.length,
      totalSize: resources.reduce((sum, r) => sum + r.size, 0),
      cached: resources.filter(r => r.cached).length,
      byType
    }
  }

  /**
   * 清空指标
   */
  clear() {
    this.metrics = []
    this.apiMetrics = []
    this.componentMetrics = []
  }

  /**
   * 导出性能数据
   */
  export() {
    return {
      metrics: this.metrics,
      apiMetrics: this.apiMetrics,
      componentMetrics: this.componentMetrics,
      resources: this.getResourcePerformance()
    }
  }
}

// 创建单例
const performanceMonitor = new PerformanceMonitor()

/**
 * 初始化性能监控
 */
export function initPerformanceMonitor() {
  // 页面加载完成后收集性能数据
  if (document.readyState === 'complete') {
    performanceMonitor.collectPagePerformance()
  } else {
    window.addEventListener('load', () => {
      setTimeout(() => {
        performanceMonitor.collectPagePerformance()
        
        // 开发环境输出性能报告
        if (import.meta.env.DEV) {
          console.group('📊 Performance Report')
          console.table(performanceMonitor.getPerformanceReport())
          console.groupEnd()
        }
      }, 0)
    })
  }

  // 监听路由变化（Vue Router）
  if (window.__ROUTER__) {
    window.__ROUTER__.afterEach(() => {
      setTimeout(() => {
        performanceMonitor.collectPagePerformance()
      }, 0)
    })
  }
}

/**
 * 性能计时器
 */
export class PerformanceTimer {
  constructor(name) {
    this.name = name
    this.startTime = performance.now()
  }

  /**
   * 结束计时并记录
   */
  end() {
    const duration = Math.round(performance.now() - this.startTime)
    
    if (import.meta.env.DEV) {
      console.log(`⏱️ ${this.name}: ${duration}ms`)
    }
    
    return duration
  }
}

/**
 * 测量函数执行时间
 * @param {Function} fn - 要测量的函数
 * @param {string} name - 函数名称
 * @returns {Function} 包装后的函数
 */
export function measurePerformance(fn, name) {
  return async function(...args) {
    const timer = new PerformanceTimer(name || fn.name)
    try {
      return await fn.apply(this, args)
    } finally {
      timer.end()
    }
  }
}

export default performanceMonitor