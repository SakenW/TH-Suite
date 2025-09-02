import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { resolve } from "path";

// https://vitejs.dev/config/
export default defineConfig(async () => ({
  plugins: [react()],
  
  // Use absolute paths for Tauri
  base: '/',

  // Vite options tailored for Tauri development and only applied in `tauri dev` or `tauri build`
  //
  // 1. prevent vite from obscuring rust errors
  clearScreen: false,
  // 2. tauri expects a fixed port, fail if that port is not available
  server: {
    port: 15173,  // 使用15173端口，避免与其他服务冲突
    strictPort: true,  // 强制使用指定端口，不允许自动切换
    host: '127.0.0.1',
    watch: {
      // 3. tell vite to ignore watching `src-tauri`
      ignored: ["**/src-tauri/**"],
    },
    // 添加代理配置，避免CORS问题
    proxy: {
      '/api': {
        target: 'http://localhost:18000',  // 后端端口改为18000
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
      "@": resolve(__dirname, "src"),
      "@components": resolve(__dirname, "src/components"),
      "@pages": resolve(__dirname, "src/pages"),
      "@hooks": resolve(__dirname, "src/hooks"),
      "@utils": resolve(__dirname, "src/utils"),
      "@types": resolve(__dirname, "src/types"),
      "@stores": resolve(__dirname, "src/stores"),
      "@services": resolve(__dirname, "src/services"),
      "@assets": resolve(__dirname, "src/assets"),
      "@theme": resolve(__dirname, "src/theme"),
    },
  },
  
  build: {
    // Tauri supports es2021
    target: process.env.TAURI_PLATFORM == "windows" ? "chrome105" : "safari13",
    // don't minify for debug builds
    minify: !process.env.TAURI_DEBUG ? "esbuild" : false,
    // produce sourcemaps for debug builds
    sourcemap: !!process.env.TAURI_DEBUG,
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom'],
          mui: ['@mui/material', '@mui/icons-material'],
          router: ['react-router-dom'],
          query: ['@tanstack/react-query'],
        },
      },
    },
  },
  
  optimizeDeps: {
    exclude: ['@tauri-apps/api'],
  },
  
  define: {
    // Define global constants
    __APP_VERSION__: JSON.stringify(process.env.npm_package_version),
  },
  
  css: {
    devSourcemap: true,
  },
}));