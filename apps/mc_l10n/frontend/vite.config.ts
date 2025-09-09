import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { resolve } from 'path'

// https://vitejs.dev/config/
export default defineConfig(async () => ({
  plugins: [
    react({
      // 启用React Fast Refresh
      fastRefresh: true,
      // 启用React DevTools
      jsxImportSource: '@emotion/react',
    }),
  ],

  // Use absolute paths for Tauri
  base: '/',

  // Vite options tailored for Tauri development and only applied in `tauri dev` or `tauri build`
  //
  // 1. prevent vite from obscuring rust errors
  clearScreen: false,
  // 2. tauri expects a fixed port, fail if that port is not available
  server: {
    port: 18001, // 改为18001，避免与Trans-Hub的5173冲突
    strictPort: true, // 强制使用指定端口，不允许自动切换
    host: 'localhost', // 本地开发
    watch: {
      // 3. tell vite to ignore watching `src-tauri`
      ignored: ['**/src-tauri/**'],
    },
    // 添加代理配置，避免CORS问题
    proxy: {
      '/api': {
        target: 'http://localhost:18000', // 后端端口改为18000
        changeOrigin: true,
        secure: false,
      },
      '/health': {
        target: 'http://localhost:18000',
        changeOrigin: true,
        secure: false,
      },
      '/docs': {
        target: 'http://localhost:18000',
        changeOrigin: true,
        secure: false,
      },
    },
  },

  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
      '@components': resolve(__dirname, 'src/components'),
      '@pages': resolve(__dirname, 'src/pages'),
      '@hooks': resolve(__dirname, 'src/hooks'),
      '@utils': resolve(__dirname, 'src/utils'),
      '@types': resolve(__dirname, 'src/types'),
      '@stores': resolve(__dirname, 'src/stores'),
      '@services': resolve(__dirname, 'src/services'),
      '@assets': resolve(__dirname, 'src/assets'),
      '@theme': resolve(__dirname, 'src/theme'),
    },
  },

  build: {
    // Tauri supports modern targets - 更新为更现代的目标
    target: process.env.TAURI_PLATFORM == 'windows' ? 'chrome120' : 'safari16',
    // 优化压缩设置
    minify: !process.env.TAURI_DEBUG ? 'esbuild' : false,
    sourcemap: !!process.env.TAURI_DEBUG,
    // 增加chunk大小限制以减少警告
    chunkSizeWarningLimit: 1600,
    rollupOptions: {
      output: {
        // 优化分包策略
        manualChunks: {
          // React核心
          'react-vendor': ['react', 'react-dom'],
          // UI框架
          'mui-core': ['@mui/material'],
          'mui-icons': ['@mui/icons-material'],
          emotion: ['@emotion/react', '@emotion/styled'],
          // 路由和状态管理
          router: ['react-router-dom'],
          'state-management': ['@tanstack/react-query', 'zustand'],
          // 动画和工具
          animation: ['framer-motion'],
          utils: ['clsx', 'class-variance-authority', 'tailwind-merge'],
          // Tauri API
          tauri: ['@tauri-apps/api'],
        },
      },
    },
  },

  optimizeDeps: {
    exclude: ['@tauri-apps/api'],
    // 预构建优化
    include: [
      'react',
      'react-dom',
      '@mui/material',
      '@emotion/react',
      '@emotion/styled',
      'framer-motion',
    ],
  },

  define: {
    // Define global constants
    __APP_VERSION__: JSON.stringify(process.env.npm_package_version),
    __DEV__: JSON.stringify(!process.env.NODE_ENV || process.env.NODE_ENV === 'development'),
  },

  css: {
    devSourcemap: true,
    // CSS代码分割
    preprocessorOptions: {
      scss: {
        additionalData: `$injectedColor: orange;`,
      },
    },
  },

  // Vite 7 新特性：改进的预览服务器
  preview: {
    port: 4173,
    strictPort: false,
  },

  // 实验性特性：启用一些性能优化
  experimental: {
    // 启用渲染优化（如果可用）
  },
}))
