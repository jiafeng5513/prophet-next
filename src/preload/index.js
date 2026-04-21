const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld('electronAPI', {
  getVersion: () => process.versions,
  getPlatform: () => process.platform,
  // 通知主进程渲染进程已就绪
  rendererReady: () => ipcRenderer.send('renderer-ready'),

  // 模式切换
  switchMode: (mode) => ipcRenderer.send('switch-mode', mode),
  onModeSwitched: (callback) => ipcRenderer.on('mode-switched', (event, data) => callback(data)),

  // 标签页相关 API
  createNewTab: () => ipcRenderer.send('new-tab'),
  switchTab: (viewId) => ipcRenderer.send('switch-tab', viewId),
  closeTab: (viewId) => ipcRenderer.send('close-tab', viewId),
  openContextMenu: (viewId) => ipcRenderer.send('show-context-menu', viewId),
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
    ipcRenderer.on('tab-title-updated', (event, viewId, title) => callback(event, viewId, title)),

  // 打开开发者工具
  openDevTools: () => ipcRenderer.send('open-dev-tools-in-new-window'),

  // 关闭所有图表页面
  closeAllChartTabs: () => ipcRenderer.send('close-all-chart-tabs'),

  // 数据源设置（跨 partition 共享）
  getDataSource: () => ipcRenderer.invoke('get-data-source'),
  setDataSource: (dataSource) => ipcRenderer.send('set-data-source', dataSource),

  // Agent 面板切换
  toggleAgentPanel: (visible) => ipcRenderer.send('toggle-agent-panel', visible),

  // Agent 面板调整宽度
  resizeAgentPanel: (width) => ipcRenderer.send('resize-agent-panel', width),

  // 工作区目录
  getWorkspacePath: () => ipcRenderer.invoke('get-workspace-path'),
  setWorkspacePath: () => ipcRenderer.invoke('set-workspace-path'),
  readDirectory: (dirPath) => ipcRenderer.invoke('read-directory', dirPath),
  readFile: (filePath) => ipcRenderer.invoke('read-file', filePath),
  openFile: (filePath) => ipcRenderer.send('open-file', filePath),
  onFileOpened: (callback) => ipcRenderer.on('file-opened', (event, data) => callback(data)),
  onTabActivated: (callback) =>
    ipcRenderer.on('tab-activated', (event, viewId) => callback(viewId)),

  // Python 编辑器 - 接收打开文件消息
  onOpenFileInEditor: (callback) =>
    ipcRenderer.on('open-file-in-editor', (event, filePath) => callback(filePath)),

  // 资源管理器面板
  toggleExplorerPanel: (visible) => ipcRenderer.send('toggle-explorer-panel', visible),
  resizeExplorerPanel: (width) => ipcRenderer.send('resize-explorer-panel', width),

  // 文件操作
  createFile: (filePath) => ipcRenderer.invoke('create-file', filePath),
  createFolder: (folderPath) => ipcRenderer.invoke('create-folder', folderPath),
  renameItem: (oldPath, newPath) => ipcRenderer.invoke('rename-item', oldPath, newPath),
  deleteItem: (targetPath) => ipcRenderer.invoke('delete-item', targetPath),
  moveItem: (srcPath, destDir) => ipcRenderer.invoke('move-item', srcPath, destDir),
  saveFile: (filePath, content) => ipcRenderer.invoke('save-file', filePath, content),

  // DSA (daily_stock_analysis) 集成
  getDsaConfig: () => ipcRenderer.invoke('get-dsa-config'),
  setDsaConfig: (config) => ipcRenderer.invoke('set-dsa-config', config),
  browseDsaPath: () => ipcRenderer.invoke('browse-dsa-path'),
  browsePythonPath: () => ipcRenderer.invoke('browse-python-path'),
  startDsaServer: () => ipcRenderer.invoke('start-dsa-server'),
  stopDsaServer: () => ipcRenderer.invoke('stop-dsa-server'),
  getDsaStatus: () => ipcRenderer.invoke('get-dsa-status'),
  checkDsaHealth: () => ipcRenderer.invoke('check-dsa-health'),
  onDsaStatusChanged: (callback) =>
    ipcRenderer.on('dsa-status-changed', (event, data) => callback(data))
})
