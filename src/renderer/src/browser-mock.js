// 浏览器模式的 Electron API 模拟
// 用于在浏览器中调试而不需要 Electron 桌面客户端

function getUUID() {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID()
  }
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0
    const v = c === 'x' ? r : (r & 0x3) | 0x8
    return v.toString(16)
  })
}

// 浏览器模式的标签页管理器
class BrowserTabManager {
  constructor() {
    this.views = new Map()
    this.activeViewId = null
    this.currentMode = 'trading'
    this.modeState = {
      trading: { viewIds: new Set(), activeViewId: null },
      developing: { viewIds: new Set(), activeViewId: null },
      news: { viewId: null },
      market_analyze: { viewId: null },
      settings: { viewId: null }
    }
    this.listeners = {
      'mode-switched': [],
      'tab-created': [],
      'tab-closed': [],
      'tab-limit': [],
      'tab-loading': [],
      'tab-title-updated': [],
      'context-menu-action': []
    }
    this.contentArea = null
    this.init()
  }

  init() {
    const existingContent = document.getElementById('browser-content-area')
    if (existingContent) {
      this.contentArea = existingContent
    } else {
      this.contentArea = document.createElement('div')
      this.contentArea.id = 'browser-content-area'
      this.contentArea.style.cssText = `
        position: absolute;
        top: 66px;
        left: 48px;
        right: 0;
        bottom: 0;
        background: #2e2c29;
        overflow: hidden;
      `
      document.body.appendChild(this.contentArea)
    }

    this.messageHandler = (event) => {
      if (event.data && event.data.type === 'iframe-title-updated') {
        for (const [viewId, view] of this.views.entries()) {
          try {
            if (view.iframe.contentWindow === event.source) {
              this.emit('tab-title-updated', viewId, event.data.title)
              break
            }
          } catch (e) {
            // ignore cross-origin errors
          }
        }
      }
    }
    window.addEventListener('message', this.messageHandler)
  }

  emit(event, ...args) {
    if (this.listeners[event]) {
      this.listeners[event].forEach((callback) => {
        try {
          if (event === 'context-menu-action') {
            callback({ action: args[0]?.action, viewId: args[0]?.viewId })
          } else if (event === 'mode-switched') {
            callback(args[0])
          } else {
            callback({}, ...args)
          }
        } catch (error) {
          console.error(`Error in ${event} listener:`, error)
        }
      })
    }
  }

  createIframe(src, viewId) {
    const iframe = document.createElement('iframe')
    iframe.id = `view-${viewId}`
    iframe.style.cssText = `
      width: 100%;
      height: 100%;
      border: none;
      display: none;
    `
    iframe.src = src
    iframe.allow = 'clipboard-read; clipboard-write'
    this.contentArea.appendChild(iframe)

    this.emit('tab-loading', viewId, true)
    iframe.onload = () => {
      this.emit('tab-loading', viewId, false)
      try {
        const title = iframe.contentDocument?.title
        if (title) this.emit('tab-title-updated', viewId, title)
      } catch (e) {
        /* cross-origin */
      }
    }
    iframe.onerror = () => {
      this.emit('tab-loading', viewId, false)
    }

    return iframe
  }

  createView(type) {
    const viewId = getUUID()
    const srcMap = {
      chart: '/chart.html',
      python: '/python.html',
      settings: '/settings.html',
      placeholder: '/placeholder.html'
    }
    const iframe = this.createIframe(srcMap[type] || '/placeholder.html', viewId)
    this.views.set(viewId, { iframe, type })
    return viewId
  }

  switchMode(newMode) {
    // Save current mode active view
    if (this.currentMode === 'trading' || this.currentMode === 'developing') {
      this.modeState[this.currentMode].activeViewId = this.activeViewId
    }

    // Hide all iframes
    this.views.forEach((view) => {
      view.iframe.style.display = 'none'
    })

    this.currentMode = newMode
    const showTabBar = newMode === 'trading' || newMode === 'developing'
    const showNewTabBtn = newMode === 'trading'

    let tabs = []
    let newActiveViewId = null

    if (newMode === 'trading') {
      const state = this.modeState.trading
      if (state.viewIds.size === 0) {
        const viewId = this.createView('chart')
        state.viewIds.add(viewId)
        state.activeViewId = viewId
      }
      newActiveViewId = state.activeViewId
      state.viewIds.forEach((vid) => {
        const vd = this.views.get(vid)
        if (vd) tabs.push({ viewId: vid, title: '新标签页', type: vd.type })
      })
    } else if (newMode === 'developing') {
      const state = this.modeState.developing
      if (state.viewIds.size === 0) {
        const viewId = this.createView('python')
        state.viewIds.add(viewId)
        state.activeViewId = viewId
      }
      newActiveViewId = state.activeViewId
      state.viewIds.forEach((vid) => {
        const vd = this.views.get(vid)
        if (vd) tabs.push({ viewId: vid, title: 'Python 编辑器', type: vd.type })
      })
    } else if (newMode === 'news' || newMode === 'market_analyze') {
      const state = this.modeState[newMode]
      if (!state.viewId) {
        state.viewId = this.createView('placeholder')
      }
      newActiveViewId = state.viewId
    } else if (newMode === 'settings') {
      const state = this.modeState.settings
      if (!state.viewId) {
        state.viewId = this.createView('settings')
      }
      newActiveViewId = state.viewId
    }

    if (newActiveViewId) {
      this.activeViewId = newActiveViewId
      const view = this.views.get(newActiveViewId)
      if (view) view.iframe.style.display = 'block'
    }

    // Update content area top offset
    this.contentArea.style.top = showTabBar ? '66px' : '30px'

    this.emit('mode-switched', {
      mode: newMode,
      showTabBar,
      showNewTabBtn,
      tabs,
      activeViewId: newActiveViewId
    })
  }

  createNewTab() {
    if (this.currentMode !== 'trading') return null
    const state = this.modeState.trading
    if (state.viewIds.size >= 10) {
      this.emit('tab-limit', '最多只能创建10个标签页')
      return null
    }

    const viewId = this.createView('chart')
    state.viewIds.add(viewId)
    this.emit('tab-created', viewId)
    return viewId
  }

  switchTab(viewId) {
    if (!this.views.has(viewId)) return
    this.views.forEach((view, id) => {
      view.iframe.style.display = id === viewId ? 'block' : 'none'
    })
    this.activeViewId = viewId
  }

  closeTab(viewId) {
    // Find which mode owns this view
    let viewMode = null
    for (const [mode, state] of Object.entries(this.modeState)) {
      if (state.viewIds && state.viewIds.has(viewId)) {
        viewMode = mode
        break
      }
    }

    if (viewMode && this.modeState[viewMode].viewIds.size <= 1) {
      this.emit('tab-limit', '至少需要保留1个标签页')
      return
    }

    const view = this.views.get(viewId)
    if (view) {
      view.iframe.remove()
      this.views.delete(viewId)
      if (viewMode && this.modeState[viewMode].viewIds) {
        this.modeState[viewMode].viewIds.delete(viewId)
      }

      if (this.activeViewId === viewId && viewMode) {
        const remaining = Array.from(this.modeState[viewMode].viewIds)
        if (remaining.length > 0) {
          this.switchTab(remaining[remaining.length - 1])
        }
      }

      this.emit('tab-closed', viewId)
    }
  }

  closeAllChartTabs() {
    const state = this.modeState.trading
    const chartViewIds = Array.from(state.viewIds)

    chartViewIds.forEach((viewId) => {
      const viewData = this.views.get(viewId)
      if (viewData) {
        viewData.iframe.remove()
        this.views.delete(viewId)
        state.viewIds.delete(viewId)
        this.emit('tab-closed', viewId)
      }
    })

    state.activeViewId = null

    if (this.currentMode === 'trading') {
      const viewId = this.createView('chart')
      state.viewIds.add(viewId)
      state.activeViewId = viewId
      this.emit('tab-created', viewId)
      this.switchTab(viewId)
    }
  }

  openContextMenu(viewId) {
    console.log('打开右键菜单:', viewId)
  }

  openDevTools() {
    console.log('打开开发者工具')
  }
}

// 创建全局标签页管理器实例
const tabManager = new BrowserTabManager()

// 模拟 Electron API
window.electronAPI = {
  getVersion: () => ({
    electron: 'browser-mode',
    chrome: navigator.userAgent.match(/Chrome\/(\d+)/)?.[1] || 'unknown',
    node: 'browser-mode',
    v8: 'browser-mode'
  }),

  getPlatform: () => {
    if (navigator.userAgent.includes('Win')) return 'win32'
    if (navigator.userAgent.includes('Mac')) return 'darwin'
    return 'linux'
  },

  rendererReady: () => {
    tabManager.switchMode('trading')
  },

  switchMode: (mode) => {
    tabManager.switchMode(mode)
  },

  onModeSwitched: (callback) => {
    if (!tabManager.listeners['mode-switched']) {
      tabManager.listeners['mode-switched'] = []
    }
    tabManager.listeners['mode-switched'].push(callback)
  },

  createNewTab: () => {
    tabManager.createNewTab()
  },

  switchTab: (viewId) => {
    tabManager.switchTab(viewId)
  },

  closeTab: (viewId) => {
    tabManager.closeTab(viewId)
  },

  openContextMenu: (viewId) => {
    tabManager.openContextMenu(viewId)
  },

  onTabCreated: (callback) => {
    tabManager.listeners['tab-created'].push(callback)
  },

  onTabClosed: (callback) => {
    tabManager.listeners['tab-closed'].push(callback)
  },

  onContextMenuPushed: (callback) => {
    tabManager.listeners['context-menu-action'].push(callback)
  },

  onTabLimit: (callback) => {
    tabManager.listeners['tab-limit'].push(callback)
  },

  onTabLoading: (callback) => {
    tabManager.listeners['tab-loading'].push(callback)
  },

  onTabTitleUpdated: (callback) => {
    tabManager.listeners['tab-title-updated'].push(callback)
  },

  openDevTools: () => {
    tabManager.openDevTools()
  },

  closeAllChartTabs: () => {
    tabManager.closeAllChartTabs()
  },

  getDataSource: () => Promise.resolve('binance'),
  setDataSource: (ds) => console.log('[browser-mock] setDataSource:', ds),

  toggleAgentPanel: (visible) => {
    console.log('[browser-mock] Agent panel:', visible ? 'show' : 'hide')
  },

  resizeAgentPanel: (width) => {
    console.log('[browser-mock] Agent panel width:', width)
  },

  // 工作区相关
  getWorkspacePath: () => Promise.resolve('/mock/ProphetWorkSpace'),
  setWorkspacePath: () => {
    console.log('[browser-mock] setWorkspacePath called')
    return Promise.resolve(null)
  },
  readDirectory: (dirPath) => {
    console.log('[browser-mock] readDirectory:', dirPath)
    // 返回模拟的文件树
    return Promise.resolve([
      {
        name: 'indicator',
        path: dirPath + '/indicator',
        isDirectory: true
      },
      {
        name: 'strategy',
        path: dirPath + '/strategy',
        isDirectory: true
      }
    ])
  },
  readFile: (filePath) => {
    console.log('[browser-mock] readFile:', filePath)
    return Promise.resolve('# Mock file content\nprint("Hello from mock")\n')
  },
  openFile: (filePath) => {
    console.log('[browser-mock] openFile:', filePath)
    const fileName = filePath.split('/').pop()
    const viewId = getUUID()
    const state = tabManager.modeState.developing
    const iframe = tabManager.createIframe('/python.html', viewId)
    tabManager.views.set(viewId, { iframe, type: 'python' })
    state.viewIds.add(viewId)
    state.activeViewId = viewId
    tabManager.switchTab(viewId)
    tabManager.emit('file-opened', { viewId, title: fileName })
  },
  onFileOpened: (callback) => {
    if (!tabManager.listeners['file-opened']) tabManager.listeners['file-opened'] = []
    tabManager.listeners['file-opened'].push(callback)
  },
  onTabActivated: (callback) => {
    if (!tabManager.listeners['tab-activated']) tabManager.listeners['tab-activated'] = []
    tabManager.listeners['tab-activated'].push(callback)
  },
  onOpenFileInEditor: (callback) => {
    console.log('[browser-mock] onOpenFileInEditor registered')
  },

  // 资源管理器面板
  toggleExplorerPanel: (visible) => {
    console.log('[browser-mock] Explorer panel:', visible ? 'show' : 'hide')
  },
  resizeExplorerPanel: (width) => {
    console.log('[browser-mock] Explorer panel width:', width)
  },

  // 文件操作
  createFile: (filePath) => {
    console.log('[browser-mock] createFile:', filePath)
    return Promise.resolve({ success: true })
  },
  createFolder: (folderPath) => {
    console.log('[browser-mock] createFolder:', folderPath)
    return Promise.resolve({ success: true })
  },
  renameItem: (oldPath, newPath) => {
    console.log('[browser-mock] renameItem:', oldPath, '->', newPath)
    return Promise.resolve({ success: true })
  },
  deleteItem: (targetPath) => {
    console.log('[browser-mock] deleteItem:', targetPath)
    return Promise.resolve({ success: true })
  },
  moveItem: (srcPath, destDir) => {
    console.log('[browser-mock] moveItem:', srcPath, '->', destDir)
    return Promise.resolve({ success: true })
  },
  saveFile: (filePath) => {
    console.log('[browser-mock] saveFile:', filePath)
    return Promise.resolve({ success: true })
  },

  removeAllListeners: () => {
    Object.keys(tabManager.listeners).forEach((key) => {
      tabManager.listeners[key] = []
    })
  }
}

console.log('✅ 浏览器模式 Electron API 模拟已加载')
