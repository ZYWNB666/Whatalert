/**
 * 应用入口文件
 *
 * 初始化 Vue 应用、插件和全局配置
 */
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import zhCn from 'element-plus/es/locale/lang/zh-cn'

import App from './App.vue'
import router from './router'
import { setupGlobalErrorHandler } from '@/utils/errorHandler'
import { initPerformanceMonitor } from '@/utils/performance'

// 创建应用实例
const app = createApp(App)

// 设置全局错误处理
setupGlobalErrorHandler()

// Vue 错误处理器
app.config.errorHandler = (err, instance, info) => {
  console.error('Vue Error:', err)
  console.error('Error Info:', info)
  
  // 只在生产环境上报错误
  if (import.meta.env.PROD) {
    // TODO: 上报到错误追踪服务
  }
}

// Vue 警告处理器（仅开发环境）
if (import.meta.env.DEV) {
  app.config.warnHandler = (msg, instance, trace) => {
    // 只记录警告，不阻止执行
    console.warn('Vue Warning:', msg)
  }
}

// 注册所有 Element Plus 图标
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

// 注册插件
app.use(createPinia())
app.use(router)
app.use(ElementPlus, {
  locale: zhCn,
  size: 'default',
  zIndex: 3000
})

// 全局属性
app.config.globalProperties.$appVersion = __APP_VERSION__
app.config.globalProperties.$buildTime = __BUILD_TIME__

// 挂载应用
app.mount('#app')

// 初始化性能监控
initPerformanceMonitor()

// 开发环境输出应用信息
if (import.meta.env.DEV) {
  console.log('%c Whatalert ', 'background: #409EFF; color: #fff; padding: 4px 8px; border-radius: 4px;')
  console.log('Version:', __APP_VERSION__)
  console.log('Build Time:', __BUILD_TIME__)
  console.log('Mode:', import.meta.env.MODE)
}

// 导出 router 供性能监控使用
window.__ROUTER__ = router

