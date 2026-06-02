/**
 * 指标编辑器窗口管理 (Electron 主进程)
 *
 * 单例模式: 全局只有一个指标编辑器窗口
 * 触发方式: 图表页指标选择 → 编辑 / 状态栏 </> 按钮 / Ctrl+Shift+E
 */

import { BrowserWindow, ipcMain } from 'electron'
import { join } from 'path'
import { is } from '@electron-toolkit/utils'
import { setEditorWindowRef } from './indicatorManager'

let editorWindow = null
let mainWindowRef = null

/**
 * 初始化指标编辑器 IPC (在 app ready 后调用)
 * @param {BrowserWindow} mainWindow
 */
export function initIndicatorEditorIPC(mainWindow) {
  mainWindowRef = mainWindow

  // 打开/聚焦编辑器窗口
  ipcMain.handle('indicator:open-editor', (_event, options) => {
    openIndicatorEditor(options)
  })

  // 切换编辑器窗口
  ipcMain.handle('indicator:toggle-editor', (_event, options) => {
    toggleIndicatorEditor(options)
  })
}

/**
 * 切换编辑器窗口 (打开/聚焦)
 */
function toggleIndicatorEditor(options = {}) {
  if (editorWindow && !editorWindow.isDestroyed()) {
    editorWindow.focus()
  } else {
    openIndicatorEditor(options)
  }
}

/**
 * 打开指标编辑器窗口
 * @param {{ indicatorId?: string }} options
 */
export function openIndicatorEditor(options = {}) {
  if (editorWindow && !editorWindow.isDestroyed()) {
    editorWindow.focus()
    // 如果指定了 indicatorId，通知编辑器切换到该指标
    if (options.indicatorId) {
      editorWindow.webContents.send('indicator:navigate-to', { id: options.indicatorId })
    }
    return
  }

  const preloadPath = join(__dirname, '../preload/indicatorEditor.js')

  editorWindow = new BrowserWindow({
    width: 1100,
    height: 700,
    minWidth: 800,
    minHeight: 500,
    parent: mainWindowRef,
    modal: false,
    title: 'Prophet 指标编辑器',
    autoHideMenuBar: true,
    backgroundColor: '#1e1e1e',
    webPreferences: {
      preload: preloadPath,
      sandbox: true,
      contextIsolation: true
    }
  })

  // 注册到 indicatorManager 以便接收文件变化通知
  setEditorWindowRef(editorWindow)

  // 构建 URL query
  const queryParams = new URLSearchParams()
  if (options.indicatorId) queryParams.set('indicatorId', options.indicatorId)
  const queryString = queryParams.toString()

  if (is.dev && process.env['ELECTRON_RENDERER_URL']) {
    const baseUrl = process.env['ELECTRON_RENDERER_URL']
    const url = `${baseUrl}/indicator-editor.html${queryString ? '?' + queryString : ''}`
    editorWindow.loadURL(url)
  } else {
    editorWindow.loadFile(join(__dirname, '../renderer/indicator-editor.html'), {
      query: queryString ? Object.fromEntries(queryParams) : undefined
    })
  }

  editorWindow.on('closed', () => {
    editorWindow = null
    setEditorWindowRef(null)
  })
}

/**
 * 关闭编辑器窗口
 */
export function closeIndicatorEditor() {
  if (editorWindow && !editorWindow.isDestroyed()) {
    editorWindow.close()
    editorWindow = null
  }
}

/**
 * 获取编辑器窗口引用
 */
export function getIndicatorEditorWindow() {
  return editorWindow && !editorWindow.isDestroyed() ? editorWindow : null
}
