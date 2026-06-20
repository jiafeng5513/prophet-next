/**
 * 自定义指标管理器 (Electron 主进程)
 *
 * 职责:
 * - 扫描 ProphetWorkSpace/indicator/ 目录
 * - 读写指标代码和 manifest
 * - 监听文件变化，通知渲染进程热加载
 * - 创建/删除指标
 */

import { ipcMain, shell, app } from 'electron'
import { join } from 'path'
import {
  existsSync,
  mkdirSync,
  readFileSync,
  writeFileSync,
  readdirSync,
  statSync,
  rmSync,
  watch
} from 'fs'
import { exec } from 'child_process'

let mainWindowRef = null
let editorWindowRef = null // 由 indicatorEditorWindow 设置
let indicatorDir = ''
let fileWatcher = null
let debounceTimers = new Map()

/**
 * 初始化指标管理器
 * @param {BrowserWindow} mainWindow
 * @param {string} workspacePath - ProphetWorkSpace 根路径
 */
export function initIndicatorManager(mainWindow, workspacePath) {
  mainWindowRef = mainWindow
  indicatorDir = join(workspacePath, 'indicator')

  // 确保目录存在
  if (!existsSync(indicatorDir)) {
    mkdirSync(indicatorDir, { recursive: true })
  }

  registerIPC()
  startFileWatcher()
}

/**
 * 设置编辑器窗口引用（由 indicatorEditorWindow 调用）
 */
export function setEditorWindowRef(win) {
  editorWindowRef = win
}

/**
 * 更新工作区路径（当用户切换工作区时）
 */
export function updateIndicatorDir(workspacePath) {
  stopFileWatcher()
  indicatorDir = join(workspacePath, 'indicator')
  if (!existsSync(indicatorDir)) {
    mkdirSync(indicatorDir, { recursive: true })
  }
  startFileWatcher()
}

/**
 * 获取指标目录路径
 */
export function getIndicatorDir() {
  return indicatorDir
}

// =====================
// IPC 通道注册
// =====================

function registerIPC() {
  // 获取所有自定义指标列表
  ipcMain.handle('indicator:list', () => {
    return listIndicators()
  })

  // 读取指定指标代码
  ipcMain.handle('indicator:read', (_event, { id }) => {
    return readIndicator(id)
  })

  // 保存指标代码
  ipcMain.handle('indicator:save', (_event, { id, code, manifest }) => {
    return saveIndicator(id, code, manifest)
  })

  // 创建新指标
  ipcMain.handle('indicator:create', (_event, { name, id }) => {
    return createIndicator(name, id)
  })

  // 删除指标
  ipcMain.handle('indicator:delete', (_event, { id }) => {
    return deleteIndicator(id)
  })

  // 用外部编辑器打开
  ipcMain.handle('indicator:open-external', (_event, { id }) => {
    return openInExternalEditor(id)
  })

  // 获取所有已启用指标的代码（供图表加载用）
  ipcMain.handle('indicator:get-active-indicators', () => {
    return getActiveIndicators()
  })
}

// =====================
// 指标文件操作
// =====================

/**
 * 列出所有自定义指标
 * @returns {{ id: string, name: string, version: string, overlay: boolean, description: string }[]}
 */
function listIndicators() {
  if (!existsSync(indicatorDir)) return []

  const entries = readdirSync(indicatorDir, { withFileTypes: true })
  const indicators = []

  for (const entry of entries) {
    if (!entry.isDirectory()) continue
    const manifestPath = join(indicatorDir, entry.name, 'manifest.json')
    if (!existsSync(manifestPath)) continue

    try {
      const manifest = JSON.parse(readFileSync(manifestPath, 'utf-8'))
      indicators.push({
        id: manifest.id || entry.name,
        name: manifest.name || entry.name,
        version: manifest.version || '1.0.0',
        overlay: manifest.overlay !== false,
        description: manifest.description || ''
      })
    } catch (e) {
      console.error(`[IndicatorManager] 读取 manifest 失败: ${entry.name}`, e)
    }
  }

  return indicators
}

/**
 * 读取指定指标的完整信息
 * @param {string} id
 * @returns {{ manifest: object, code: string } | null}
 */
function readIndicator(id) {
  const dir = join(indicatorDir, id)
  const manifestPath = join(dir, 'manifest.json')
  const codePath = join(dir, 'index.js')

  if (!existsSync(manifestPath) || !existsSync(codePath)) {
    return null
  }

  try {
    const manifest = JSON.parse(readFileSync(manifestPath, 'utf-8'))
    const code = readFileSync(codePath, 'utf-8')
    return { manifest, code }
  } catch (e) {
    console.error(`[IndicatorManager] 读取指标失败: ${id}`, e)
    return null
  }
}

/**
 * 保存指标代码和 manifest
 */
function saveIndicator(id, code, manifest) {
  const dir = join(indicatorDir, id)
  if (!existsSync(dir)) {
    mkdirSync(dir, { recursive: true })
  }

  try {
    if (code !== undefined) {
      writeFileSync(join(dir, 'index.js'), code, 'utf-8')
    }
    if (manifest !== undefined) {
      manifest.modified = new Date().toISOString()
      writeFileSync(join(dir, 'manifest.json'), JSON.stringify(manifest, null, 2), 'utf-8')
    }

    // 通知图表渲染进程热加载
    notifyCodeUpdated(id, code)

    return { success: true }
  } catch (e) {
    console.error(`[IndicatorManager] 保存指标失败: ${id}`, e)
    return { success: false, error: e.message }
  }
}

/**
 * 创建新指标（含模板）
 */
function createIndicator(name, id) {
  // 安全检查: id 只允许小写字母、数字、连字符
  if (!/^[a-z0-9][a-z0-9-]*$/.test(id)) {
    return { success: false, error: 'ID 只允许小写字母、数字和连字符，且不能以连字符开头' }
  }

  const dir = join(indicatorDir, id)
  if (existsSync(dir)) {
    return { success: false, error: `指标 "${id}" 已存在` }
  }

  mkdirSync(dir, { recursive: true })

  const manifest = {
    name,
    id,
    version: '1.0.0',
    overlay: true,
    description: '',
    created: new Date().toISOString(),
    modified: new Date().toISOString()
  }

  const templateCode = generateTemplate(name, id)

  writeFileSync(join(dir, 'manifest.json'), JSON.stringify(manifest, null, 2), 'utf-8')
  writeFileSync(join(dir, 'index.js'), templateCode, 'utf-8')

  return { success: true, manifest, code: templateCode }
}

/**
 * 删除指标
 */
function deleteIndicator(id) {
  const dir = join(indicatorDir, id)
  if (!existsSync(dir)) {
    return { success: false, error: `指标 "${id}" 不存在` }
  }

  try {
    rmSync(dir, { recursive: true, force: true })

    // 通知图表移除该指标
    if (mainWindowRef && !mainWindowRef.isDestroyed()) {
      mainWindowRef.webContents.send('indicator:removed', { id })
    }

    return { success: true }
  } catch (e) {
    return { success: false, error: e.message }
  }
}

/**
 * 获取所有已启用指标的代码
 */
function getActiveIndicators() {
  const indicators = listIndicators()
  const result = []

  for (const ind of indicators) {
    const codePath = join(indicatorDir, ind.id, 'index.js')
    if (!existsSync(codePath)) continue

    try {
      const code = readFileSync(codePath, 'utf-8')
      result.push({ id: ind.id, name: ind.name, code, overlay: ind.overlay })
    } catch (e) {
      console.error(`[IndicatorManager] 读取代码失败: ${ind.id}`, e)
    }
  }

  return result
}

// =====================
// 外部编辑器
// =====================

function getConfiguredEditor() {
  try {
    const configPath = join(app.getPath('userData'), 'hivelogic-config.json')
    if (existsSync(configPath)) {
      const config = JSON.parse(readFileSync(configPath, 'utf-8'))
      return config.externalEditor || 'auto'
    }
  } catch { /* ignore */ }
  return 'auto'
}

function openInExternalEditor(id) {
  const filePath = join(indicatorDir, id, 'index.js')
  if (!existsSync(filePath)) {
    return { success: false, error: '文件不存在' }
  }

  const editor = getConfiguredEditor()

  if (editor === 'auto') {
    // 按优先级: cursor → code → 系统默认
    const candidates = ['cursor', 'code']
    for (const cmd of candidates) {
      try {
        exec(`${cmd} "${filePath}"`, (err) => {
          if (err) return
        })
        return { success: true }
      } catch {
        continue
      }
    }
    shell.openPath(filePath)
    return { success: true }
  }

  // 指定编辑器
  const cmd = editor === 'vscode' ? 'code' : editor
  try {
    exec(`${cmd} "${filePath}"`)
    return { success: true }
  } catch {
    shell.openPath(filePath)
    return { success: true }
  }
}

// =====================
// 文件监听
// =====================

function startFileWatcher() {
  if (!existsSync(indicatorDir)) return

  try {
    fileWatcher = watch(indicatorDir, { recursive: true }, (eventType, filename) => {
      if (!filename || !filename.endsWith('.js')) return

      // 从路径中提取 indicator id (第一级目录名)
      const parts = filename.split(/[\\/]/)
      if (parts.length < 2) return
      const indicatorId = parts[0]

      // 防抖 500ms
      if (debounceTimers.has(indicatorId)) {
        clearTimeout(debounceTimers.get(indicatorId))
      }

      debounceTimers.set(indicatorId, setTimeout(() => {
        debounceTimers.delete(indicatorId)
        handleFileChange(indicatorId)
      }, 500))
    })
  } catch (e) {
    console.error('[IndicatorManager] 文件监听启动失败:', e)
  }
}

function stopFileWatcher() {
  if (fileWatcher) {
    fileWatcher.close()
    fileWatcher = null
  }
  for (const timer of debounceTimers.values()) {
    clearTimeout(timer)
  }
  debounceTimers.clear()
}

function handleFileChange(indicatorId) {
  const codePath = join(indicatorDir, indicatorId, 'index.js')
  if (!existsSync(codePath)) return

  try {
    const code = readFileSync(codePath, 'utf-8')

    // 通知编辑器窗口刷新
    if (editorWindowRef && !editorWindowRef.isDestroyed()) {
      editorWindowRef.webContents.send('indicator:file-changed', { id: indicatorId, code })
    }

    // 通知图表热加载
    notifyCodeUpdated(indicatorId, code)
  } catch (e) {
    console.error(`[IndicatorManager] 处理文件变化失败: ${indicatorId}`, e)
  }
}

function notifyCodeUpdated(indicatorId, code) {
  if (mainWindowRef && !mainWindowRef.isDestroyed()) {
    mainWindowRef.webContents.send('indicator:code-updated', { id: indicatorId, code })
  }
}

// =====================
// 模板生成
// =====================

function generateTemplate(name, id) {
  const pascalName = id
    .split('-')
    .map((s) => s.charAt(0).toUpperCase() + s.slice(1))
    .join('')

  return `/**
 * ${name}
 * 自定义技术指标
 */

/**
 * @param {object} PineJS - TradingView PineJS 运行时对象
 * @returns {object} CustomIndicator
 */
export function create(PineJS) {
  return {
    name: '${pascalName}',

    metainfo: {
      _metainfoVersion: 53,
      id: '${pascalName}@tv-basicstudies-1',
      name: '${pascalName}',
      description: '${name}',
      shortDescription: '${pascalName}',
      is_price_study: true,
      isCustomIndicator: true,
      linkedToSeries: true,
      format: { type: 'inherit' },

      plots: [
        { id: 'plot0', type: 'line' }
      ],

      defaults: {
        styles: {
          plot0: { linestyle: 0, linewidth: 2, plottype: 2, trackPrice: false, transparency: 0, color: '#2196F3', visible: true }
        },
        inputs: {
          length: 20
        }
      },

      styles: {
        plot0: { title: 'Value', histogramBase: 0 }
      },

      inputs: [
        { id: 'length', name: 'Length', type: 'integer', defval: 20, min: 1, max: 500 }
      ]
    },

    constructor: function () {
      this.main = function (context, inputCallback) {
        this._context = context
        this._input = inputCallback

        var length = this._input(0)
        var close = this._context.new_var(PineJS.Std.close(this._context))

        return [
          PineJS.Std.sma(close, length, this._context)
        ]
      }
    }
  }
}
`
}

/**
 * 清理资源
 */
export function destroyIndicatorManager() {
  stopFileWatcher()
}
