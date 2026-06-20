/**
 * 指标编辑器窗口专用 preload 脚本
 *
 * 只暴露编辑器窗口所需的最小 API 集合
 */
const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld('indicatorEditorAPI', {
  // 指标管理
  listIndicators: () => ipcRenderer.invoke('indicator:list'),
  readIndicator: (id) => ipcRenderer.invoke('indicator:read', { id }),
  saveIndicator: (id, code, manifest) => ipcRenderer.invoke('indicator:save', { id, code, manifest }),
  createIndicator: (name, id) => ipcRenderer.invoke('indicator:create', { name, id }),
  deleteIndicator: (id) => ipcRenderer.invoke('indicator:delete', { id }),
  openExternal: (id) => ipcRenderer.invoke('indicator:open-external', { id }),

  // 事件监听
  onFileChanged: (callback) =>
    ipcRenderer.on('indicator:file-changed', (event, data) => callback(data)),
  onNavigateTo: (callback) =>
    ipcRenderer.on('indicator:navigate-to', (event, data) => callback(data)),
  onReloadResult: (callback) =>
    ipcRenderer.on('indicator:reload-result', (event, data) => callback(data))
})
