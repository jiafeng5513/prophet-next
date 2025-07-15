const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld('electronAPI', {
  getVersion: () => process.versions,
  // 添加标签页相关 API
  createHomeTab: () => ipcRenderer.send('home-tab'),
  createNewTab: () => ipcRenderer.send('new-tab'),
  switchTab: (viewId) => ipcRenderer.send('switch-tab', viewId),
  closeTab: (viewId) => ipcRenderer.send('close-tab', viewId),
  openContextMenu: (viewId) => ipcRenderer.send('show-context-menu', viewId),
  onHomeCreated: (callback) => ipcRenderer.on('home-created', callback),
  onTabCreated: (callback) => ipcRenderer.on('tab-created', callback),
  onTabClosed: (callback) => ipcRenderer.on('tab-closed', callback),
  onContextMenuPushed: (callback) =>
    ipcRenderer.on('context-menu-action', (event, data) => callback(data)),

  // 添加标签限制提示的监听器
  onTabLimit: (callback) => ipcRenderer.on('tab-limit', (event, message) => callback(message)),

  // 添加加载状态监听
  onTabLoading: (callback) =>
    ipcRenderer.on('tab-loading', (event, viewId, isLoading) => callback(viewId, isLoading)),

  // 添加标题更新监听
  onTabTitleUpdated: (callback) =>
    ipcRenderer.on('tab-title-updated', (event, viewId, title) => callback(viewId, title))
})
