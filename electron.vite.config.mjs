import { resolve } from 'path'
import { defineConfig, externalizeDepsPlugin } from 'electron-vite'
import vue from '@vitejs/plugin-vue'
import MonacoEditorPluginCjs from 'vite-plugin-monaco-editor'
const monacoEditorPlugin =
  MonacoEditorPluginCjs && MonacoEditorPluginCjs.default
    ? MonacoEditorPluginCjs.default
    : MonacoEditorPluginCjs

console.log('✅ 配置文件已加载 -', new Date().toLocaleTimeString())

export default defineConfig({
  main: {
    build: { outDir: 'out/main' },
    plugins: [externalizeDepsPlugin()]
  },
  preload: {
    build: { outDir: 'out/preload' },
    plugins: [externalizeDepsPlugin()]
  },
  renderer: {
    logLevel: 'debug', // 强制开启调试日志
    root: resolve(__dirname, 'src/renderer'),
    build: {
      minify: false, // 关闭压缩便于调试
      sourcemap: 'inline', // 生成源码映射
      outDir: 'out/renderer',
      emptyOutDir: true,
      rollupOptions: {
        input: {
          browser: resolve(__dirname, 'src/renderer/index.html'),
          webview: resolve(__dirname, 'src/renderer/home.html'),
          chart: resolve(__dirname, 'src/renderer/chart.html'),
          python: resolve(__dirname, 'src/renderer/python.html'),
          settings: resolve(__dirname, 'src/renderer/settings.html'),
          placeholder: resolve(__dirname, 'src/renderer/placeholder.html')
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
      // MonacoEditorPlugin({ languages: ['python'] }),
      monacoEditorPlugin({ languages: ['python'] }),
      {
        name: 'debug-plugin',
        // 使用更早的钩子
        config(config) {
          console.log('⚡ Renderer 配置已加载')
          console.log('输出目录:', config.build?.outDir || '未定义')
          return null
        },
        // 添加错误捕获
        buildStart() {
          console.log('🚀 Renderer 构建已启动')
        }
      }
    ]
  }
})
