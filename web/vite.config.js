import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  // 加载环境变量
  const env = loadEnv(mode, process.cwd())
  
  return {
    plugins: [vue()],
    
    // 路径别名
    resolve: {
      alias: {
        '@': resolve(__dirname, 'src'),
        '@components': resolve(__dirname, 'src/components'),
        '@views': resolve(__dirname, 'src/views'),
        '@utils': resolve(__dirname, 'src/utils'),
        '@api': resolve(__dirname, 'src/api'),
        '@stores': resolve(__dirname, 'src/stores'),
        '@assets': resolve(__dirname, 'src/assets')
      }
    },
    
    // 开发服务器配置
    server: {
      port: 3000,
      host: '0.0.0.0',
      open: true,
      // API 代理配置
      proxy: {
        '/api': {
          target: env.VITE_API_BASE_URL || 'http://localhost:8000',
          changeOrigin: true,
          rewrite: (path) => path
        }
      }
    },
    
    // 构建配置
    build: {
      // 输出目录
      outDir: 'dist',
      // 资源目录
      assetsDir: 'assets',
      // 启用 CSS 代码分割
      cssCodeSplit: true,
      // 构建后是否生成 source map
      sourcemap: mode === 'development',
      // 消除打包大小超过 500kb 警告
      chunkSizeWarningLimit: 2000,
      // 压缩配置
      minify: 'terser',
      terserOptions: {
        compress: {
          // 生产环境移除 console
          drop_console: mode === 'production',
          drop_debugger: mode === 'production'
        }
      },
      // Rollup 配置
      rollupOptions: {
        output: {
          // 代码分割
          manualChunks: {
            // Vue 核心
            'vue-vendor': ['vue', 'vue-router', 'pinia'],
            // Element Plus
            'element-plus': ['element-plus', '@element-plus/icons-vue'],
            // 图表库
            'charts': ['echarts', 'vue-echarts'],
            // 工具库
            'utils': ['axios', 'dayjs']
          },
          // 资源文件命名
          chunkFileNames: 'js/[name]-[hash].js',
          entryFileNames: 'js/[name]-[hash].js',
          assetFileNames: (assetInfo) => {
            // 根据文件类型分类存放
            const info = assetInfo.name.split('.')
            let extType = info[info.length - 1]
            
            if (/\.(png|jpe?g|gif|svg|webp|ico)$/i.test(assetInfo.name)) {
              extType = 'images'
            } else if (/\.(woff2?|eot|ttf|otf)$/i.test(assetInfo.name)) {
              extType = 'fonts'
            } else if (/\.css$/i.test(assetInfo.name)) {
              extType = 'css'
            }
            
            return `${extType}/[name]-[hash][extname]`
          }
        }
      }
    },
    
    // 优化配置
    optimizeDeps: {
      include: [
        'vue',
        'vue-router',
        'pinia',
        'element-plus',
        '@element-plus/icons-vue',
        'axios',
        'dayjs',
        'echarts',
        'vue-echarts'
      ]
    },
    
    // CSS 配置
    css: {
      preprocessorOptions: {
        scss: {
          // 如果需要全局 SCSS 变量，请先创建 src/styles/variables.scss 文件
          // additionalData: `@use "@/styles/variables.scss" as *;`
        }
      }
    },
    
    // 定义全局常量
    define: {
      __APP_VERSION__: JSON.stringify(process.env.npm_package_version),
      __BUILD_TIME__: JSON.stringify(new Date().toISOString())
    }
  }
})
