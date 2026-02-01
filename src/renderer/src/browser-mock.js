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
    this.homeViewId = null
    this.listeners = {
      'home-created': [],
      'settings-created': [],
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
    // 创建内容区域容器
    const existingContent = document.getElementById('browser-content-area')
    if (existingContent) {
      this.contentArea = existingContent
    } else {
      this.contentArea = document.createElement('div')
      this.contentArea.id = 'browser-content-area'
      this.contentArea.style.cssText = `
        position: absolute;
        top: 40px;
        left: 0;
        right: 0;
        bottom: 0;
        background: #2e2c29;
        overflow: hidden;
      `
      document.body.appendChild(this.contentArea)
    }

    // 统一的消息处理器，用于接收来自所有 iframe 的消息
    this.messageHandler = (event) => {
      // 验证消息类型
      if (event.data && event.data.type === 'iframe-title-updated') {
        console.log('[BrowserTabManager] Received iframe-title-updated message:', event.data.title)
        console.log('[BrowserTabManager] event.source:', event.source)
        console.log('[BrowserTabManager] Current views:', Array.from(this.views.keys()))

        // 通过 event.source 找到对应的 viewId
        let found = false
        for (const [viewId, view] of this.views.entries()) {
          try {
            const iframeWindow = view.iframe.contentWindow
            console.log(`[BrowserTabManager] Checking viewId ${viewId}, iframe.contentWindow:`, iframeWindow)
            
            // 直接比较
            if (iframeWindow === event.source) {
              console.log('[BrowserTabManager] Matched! Updating title for viewId:', viewId, 'title:', event.data.title)
              this.emit('tab-title-updated', viewId, event.data.title)
              found = true
              break
            }
            
            // 备用方案：通过 iframe 元素查找
            // 如果直接比较失败，尝试通过遍历所有 iframe 来匹配
            if (!found) {
              const allIframes = this.contentArea.querySelectorAll('iframe')
              for (const iframe of allIframes) {
                if (iframe.contentWindow === event.source && iframe.id === `view-${viewId}`) {
                  console.log('[BrowserTabManager] Matched via iframe element! Updating title for viewId:', viewId, 'title:', event.data.title)
                  this.emit('tab-title-updated', viewId, event.data.title)
                  found = true
                  break
                }
              }
            }
          } catch (e) {
            console.warn(`[BrowserTabManager] Error checking viewId ${viewId}:`, e)
          }
        }

        if (!found) {
          console.warn('[BrowserTabManager] Could not find matching iframe for message source')
          // 如果找不到匹配的 iframe，尝试更新当前活动的标签页
          if (this.activeViewId) {
            console.log('[BrowserTabManager] Fallback: updating active tab:', this.activeViewId)
            this.emit('tab-title-updated', this.activeViewId, event.data.title)
          }
        }
      }
    }
    // 添加全局消息监听器
    window.addEventListener('message', this.messageHandler)
  }

  emit(event, ...args) {
    if (this.listeners[event]) {
      this.listeners[event].forEach((callback) => {
        try {
          // 模拟 Electron IPC 事件格式
          if (event === 'context-menu-action') {
            callback({ action: args[0]?.action, viewId: args[0]?.viewId })
          } else {
            callback({}, ...args)
          }
        } catch (error) {
          console.error(`Error in ${event} listener:`, error)
        }
      })
    }
  }

  createHomeTab() {
    if (this.views.size >= 10) {
      this.emit('tab-limit', '最多只能创建10个标签页')
      return null
    }

    const viewId = getUUID()
    const iframe = document.createElement('iframe')
    iframe.id = `view-${viewId}`
    iframe.style.cssText = `
      width: 100%;
      height: 100%;
      border: none;
      display: ${this.activeViewId === null ? 'block' : 'none'};
    `
    iframe.src = '/home.html'
    iframe.allow = 'clipboard-read; clipboard-write'

    this.contentArea.appendChild(iframe)
    this.views.set(viewId, { iframe, type: 'home' })

    if (this.activeViewId === null) {
      this.activeViewId = viewId
      this.homeViewId = viewId
    }

    // 模拟加载状态
    this.emit('tab-loading', viewId, true)
    iframe.onload = () => {
      this.emit('tab-loading', viewId, false)
      // 延迟获取标题，确保页面已完全加载
      setTimeout(() => {
        try {
          const title = iframe.contentDocument?.title || 'Home'
          this.emit('tab-title-updated', viewId, title)
        } catch (e) {
          // 跨域限制，使用默认标题
          this.emit('tab-title-updated', viewId, 'Home')
        }
      }, 100)
    }
    iframe.onerror = () => {
      this.emit('tab-loading', viewId, false)
      console.error('加载 Home 页面失败')
    }

    this.emit('home-created', viewId)
    return viewId
  }

  createNewTab() {
    if (this.views.size >= 10) {
      this.emit('tab-limit', '最多只能创建10个标签页')
      return null
    }

    const viewId = getUUID()
    const iframe = document.createElement('iframe')
    iframe.id = `view-${viewId}`
    iframe.style.cssText = `
      width: 100%;
      height: 100%;
      border: none;
      display: none;
    `
    iframe.src = '/chart.html'

    this.contentArea.appendChild(iframe)
    this.views.set(viewId, { iframe, type: 'chart' })

    // 模拟加载状态
    this.emit('tab-loading', viewId, true)
    iframe.onload = () => {
      this.emit('tab-loading', viewId, false)
      try {
        const title = iframe.contentDocument?.title || '新标签页'
        this.emit('tab-title-updated', viewId, title)
      } catch (e) {
        // 跨域限制，忽略
      }
    }

    this.emit('tab-created', viewId)
    return viewId
  }

  createSettingsTab() {
    if (this.views.size >= 10) {
      this.emit('tab-limit', '最多只能创建10个标签页')
      return null
    }

    const viewId = getUUID()
    const iframe = document.createElement('iframe')
    iframe.id = `view-${viewId}`
    iframe.style.cssText = `
      width: 100%;
      height: 100%;
      border: none;
      display: none;
    `
    iframe.src = '/settings.html'

    this.contentArea.appendChild(iframe)
    this.views.set(viewId, { iframe, type: 'settings' })

    // 模拟加载状态
    this.emit('tab-loading', viewId, true)
    iframe.onload = () => {
      this.emit('tab-loading', viewId, false)
      try {
        const title = iframe.contentDocument?.title || '设置'
        this.emit('tab-title-updated', viewId, title)
      } catch (e) {
        // 跨域限制，忽略
      }
    }

    this.emit('settings-created', viewId)
    return viewId
  }

  createPythonTab() {
    if (this.views.size >= 10) {
      this.emit('tab-limit', '最多只能创建10个标签页')
      return null
    }

    const viewId = getUUID()
    const iframe = document.createElement('iframe')
    iframe.id = `view-${viewId}`
    iframe.style.cssText = `
      width: 100%;
      height: 100%;
      border: none;
      display: none;
    `
    iframe.src = '/python.html'

    this.contentArea.appendChild(iframe)
    this.views.set(viewId, { iframe, type: 'python' })

    // 模拟加载状态
    this.emit('tab-loading', viewId, true)
    iframe.onload = () => {
      this.emit('tab-loading', viewId, false)
      try {
        const title = iframe.contentDocument?.title || 'Python 编辑器'
        this.emit('tab-title-updated', viewId, title)
      } catch (e) {
        // 跨域限制，忽略
      }
    }

    this.emit('tab-created', viewId)
    return viewId
  }

  switchTab(viewId) {
    if (!this.views.has(viewId)) return

    // 隐藏所有标签页
    this.views.forEach((view, id) => {
      view.iframe.style.display = id === viewId ? 'block' : 'none'
    })

    this.activeViewId = viewId
  }

  closeTab(viewId) {
    if (this.views.size <= 1) {
      this.emit('tab-limit', '至少需要保留1个标签页')
      return
    }

    const view = this.views.get(viewId)
    if (view) {
      view.iframe.remove()
      this.views.delete(viewId)

      // 如果关闭的是当前活动标签，切换到最后一个
      if (this.activeViewId === viewId) {
        const lastViewId = Array.from(this.views.keys())[this.views.size - 1]
        this.switchTab(lastViewId)
      }

      this.emit('tab-closed', viewId)
    }
  }

  openContextMenu(viewId) {
    // 浏览器模式下，右键菜单功能简化
    console.log('打开右键菜单:', viewId)
    // 可以在这里实现浏览器原生的右键菜单
  }

  openDevTools() {
    // 浏览器模式下，打开浏览器开发者工具
    console.log('打开开发者工具')
    // 在浏览器中，用户可以使用 F12 或右键菜单打开开发者工具
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

  createHomeTab: () => {
    tabManager.createHomeTab()
  },

  createNewTab: () => {
    tabManager.createNewTab()
  },

  createSettingsTab: () => {
    tabManager.createSettingsTab()
  },

  createPythonTab: () => {
    tabManager.createPythonTab()
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

  onHomeCreated: (callback) => {
    tabManager.listeners['home-created'].push(callback)
  },

  onSettingsCreated: (callback) => {
    tabManager.listeners['settings-created'].push(callback)
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

  removeAllListeners: () => {
    // 清理所有监听器
    Object.keys(tabManager.listeners).forEach((key) => {
      tabManager.listeners[key] = []
    })
  }
}

console.log('✅ 浏览器模式 Electron API 模拟已加载')
