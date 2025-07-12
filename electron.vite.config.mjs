import { resolve } from 'path'
import { defineConfig, externalizeDepsPlugin } from 'electron-vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  main: {
    plugins: [externalizeDepsPlugin()]
  },
  preload: {
    plugins: [externalizeDepsPlugin()]
  },
  renderer: {
    build: {
      rollupOptions: {
        input: {
          browser: resolve(__dirname, 'src/renderer/index.html'),
          webview: resolve(__dirname, 'src/renderer/home.html'),
          chart: resolve(__dirname, 'src/renderer/chart.html')
        }
      }
    },
    resolve: {
      alias: {
        '@renderer': resolve(__dirname, 'src/renderer/src'),
        '@public': resolve(__dirname, 'src/renderer/public'),
        '@services': resolve(__dirname, 'src/renderer/src/services')
      }
    },
    plugins: [vue()]
  }
})
