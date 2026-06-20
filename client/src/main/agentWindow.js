/**
 * Agent Window 窗口管理 (Electron 主进程)
 *
 * 单例模式: 全局只有一个 Agent Window
 * 触发方式: 左上角 🤖 按钮 / Ctrl+Shift+A / 侧边栏升级提示
 */

import { BrowserWindow, ipcMain } from 'electron'
import { join } from 'path'
import { is } from '@electron-toolkit/utils'

let agentWindow = null
let mainWindowRef = null

/**
 * 初始化 Agent Window IPC (在 app ready 后调用)
 * @param {BrowserWindow} mainWindow
 */
export function initAgentWindowIPC(mainWindow) {
  mainWindowRef = mainWindow

  // 打开/聚焦 Agent Window
  ipcMain.handle('agent:toggle-window', (_event, options) => {
    toggleAgentWindow(options)
  })

  // 打开指定参数的 Agent Window
  ipcMain.handle('agent:open-window', (_event, options) => {
    openAgentWindow(options)
  })

  // Agent Window 分析完成 → 同步结果到侧边栏
  ipcMain.handle('agent:sync-result', (_event, data) => {
    if (mainWindowRef && !mainWindowRef.isDestroyed()) {
      mainWindowRef.webContents.send('sidebar:agent-result', data)
    }
  })

  // Agent/侧边栏 → Chart 标签页: 添加信号标注
  ipcMain.handle('chart:add-annotations', (_event, { symbol, annotations }) => {
    if (!mainWindowRef || mainWindowRef.isDestroyed()) return

    // 向主窗口渲染进程广播标注事件，由 Chart 标签页自行消费
    mainWindowRef.webContents.send('chart:annotations-update', { symbol, annotations })
  })
}

/**
 * 切换 Agent Window (打开/聚焦)
 */
function toggleAgentWindow(options = {}) {
  if (agentWindow && !agentWindow.isDestroyed()) {
    agentWindow.focus()
  } else {
    openAgentWindow(options)
  }
}

/**
 * 打开 Agent Window
 * @param {{ symbol?: string, mode?: string, sessionId?: string }} options
 */
export function openAgentWindow(options = {}) {
  if (agentWindow && !agentWindow.isDestroyed()) {
    agentWindow.focus()
    return
  }

  const preloadPath = join(__dirname, '../preload/index.js')

  agentWindow = new BrowserWindow({
    width: 900,
    height: 750,
    minWidth: 600,
    minHeight: 500,
    parent: mainWindowRef,
    modal: false,
    title: 'AI 深度分析',
    autoHideMenuBar: true,
    backgroundColor: '#1e1e1e',
    webPreferences: {
      preload: preloadPath,
      sandbox: false
    }
  })

  // 构建 URL query
  const queryParams = new URLSearchParams()
  if (options.symbol) queryParams.set('symbol', options.symbol)
  if (options.mode) queryParams.set('mode', options.mode)
  if (options.sessionId) queryParams.set('sessionId', options.sessionId)
  const queryString = queryParams.toString()

  if (is.dev && process.env['ELECTRON_RENDERER_URL']) {
    const baseUrl = process.env['ELECTRON_RENDERER_URL']
    const url = `${baseUrl}/agent-window.html${queryString ? '?' + queryString : ''}`
    agentWindow.loadURL(url)
  } else {
    agentWindow.loadFile(join(__dirname, '../renderer/agent-window.html'), {
      query: queryString ? Object.fromEntries(queryParams) : undefined
    })
  }

  agentWindow.on('closed', () => {
    agentWindow = null
  })
}

/**
 * 关闭 Agent Window (可选)
 */
export function closeAgentWindow() {
  if (agentWindow && !agentWindow.isDestroyed()) {
    agentWindow.close()
    agentWindow = null
  }
}

/**
 * 获取 Agent Window 引用
 */
export function getAgentWindow() {
  return agentWindow && !agentWindow.isDestroyed() ? agentWindow : null
}
