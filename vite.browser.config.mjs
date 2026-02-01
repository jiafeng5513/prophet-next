import { resolve } from 'path'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import MonacoEditorPluginCjs from 'vite-plugin-monaco-editor'

const monacoEditorPlugin =
  MonacoEditorPluginCjs && MonacoEditorPluginCjs.default
    ? MonacoEditorPluginCjs.default
    : MonacoEditorPluginCjs

console.log('✅ 浏览器模式配置文件已加载 -', new Date().toLocaleTimeString())

export default defineConfig({
  root: resolve(__dirname, 'src/renderer'),
  server: {
    port: 5173,
    open: true, // 自动打开浏览器
    strictPort: false
  },
  build: {
    minify: false,
    sourcemap: 'inline',
    outDir: 'out/renderer',
    emptyOutDir: true,
    rollupOptions: {
      input: {
        browser: resolve(__dirname, 'src/renderer/index.html'),
        home: resolve(__dirname, 'src/renderer/home.html'),
        chart: resolve(__dirname, 'src/renderer/chart.html'),
        python: resolve(__dirname, 'src/renderer/python.html'),
        settings: resolve(__dirname, 'src/renderer/settings.html')
      }
    }
  },
  resolve: {
    alias: {
      '@renderer': resolve(__dirname, 'src/renderer/src'),
      '@public': resolve(__dirname, 'src/renderer/public'),
      '@tradingview': resolve(__dirname, 'src/renderer/public/tradingview'),
      '@services': resolve(__dirname, 'src/renderer/src/services')
    }
  },
  plugins: [
    vue(),
    monacoEditorPlugin({ languages: ['python'] }),
    {
      name: 'browser-mode-plugin',
      config(config) {
        console.log('⚡ 浏览器模式配置已加载')
        return null
      }
    }
  ]
})
