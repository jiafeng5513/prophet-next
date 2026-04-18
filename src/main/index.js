import { app, shell, WebContentsView, BrowserWindow, ipcMain, Menu, session } from 'electron'
import { join } from 'path'
import { is, electronApp, optimizer } from '@electron-toolkit/utils'
import icon from '../../resources/prophet_logo.png?asset'

// 全局的变量参数
const ACTIVITY_BAR_WIDTH = 48 // VSCode 风格侧边栏宽度
const TITLE_BAR_HEIGHT = 30 // 标题栏高度
const TAB_BAR_HEIGHT = 36 // 标签栏高度
const AGENT_PANEL_WIDTH = 350 // Agent 侧栏默认宽度
let agentPanelVisible = true // Agent 侧栏是否可见
let currentAgentPanelWidth = AGENT_PANEL_WIDTH // Agent 侧栏当前宽度
let mainWindow // 主进程的唯一窗口，所有tab都被它加载
let views = new Map() // 所有的view 对象，格式: { view: WebContentsView, type: string, title: string }
let activeViewId = null // 活动的view对象
let currentDataSource = 'binance' // 当前数据源设置（跨 partition 共享）

// 模式管理
let currentMode = 'trading' // 'trading' | 'developing' | 'news' | 'market_analyze' | 'settings'
const modeState = {
  trading: { viewIds: new Set(), activeViewId: null },
  developing: { viewIds: new Set(), activeViewId: null },
  news: { viewId: null },
  market_analyze: { viewId: null },
  settings: { viewId: null }
}

function createWindow() {
  // Create the browser window.
  const windowOptions = {
    width: 1600,
    height: 1000,
    show: false,
    title: 'Prophet-Next',
    autoHideMenuBar: true,
    icon,
    webPreferences: {
      preload: join(__dirname, '../preload/index.js'),
      sandbox: false
    }
  }

  if (process.platform === 'darwin') {
    // macOS: 隐藏标题栏，保留红绿灯
    windowOptions.titleBarStyle = 'hiddenInset'
    windowOptions.trafficLightPosition = { x: 12, y: 8 }
  } else {
    // Windows/Linux: 隐藏标题栏，使用原生窗口控制按钮覆盖层
    windowOptions.titleBarStyle = 'hidden'
    windowOptions.titleBarOverlay = {
      color: '#1e1e1e',
      symbolColor: '#cccccc',
      height: 30
    }
  }

  mainWindow = new BrowserWindow(windowOptions)

  mainWindow.on('ready-to-show', () => {
    mainWindow.show()
  })

  mainWindow.webContents.setWindowOpenHandler((details) => {
    shell.openExternal(details.url)
    return { action: 'deny' }
  })

  const handleWindowBoundsChange = () => {
    if (!mainWindow || !activeViewId) return
    const activeView = views.get(activeViewId)
    if (activeView) {
      updateWebViewBounds(mainWindow, activeView.view)
    }
  }

  mainWindow.on('move', handleWindowBoundsChange)
  mainWindow.on('resize', handleWindowBoundsChange)

  // HMR for renderer base on electron-vite cli.
  // Load the remote URL for development or the local html file for production.
  if (is.dev && process.env['ELECTRON_RENDERER_URL']) {
    mainWindow.loadURL(process.env['ELECTRON_RENDERER_URL'])
  } else {
    mainWindow.loadFile(join(__dirname, '../renderer/index.html'))
  }

  // 创建第一个标签页
  // createHomeTab()
  // mainWindow.webContents.openDevTools({ mode: 'left' })
}

function getUUID() {
  if (typeof crypto === 'object') {
    if (typeof crypto.randomUUID === 'function') {
      return crypto.randomUUID()
    }
    if (typeof crypto.getRandomValues === 'function' && typeof Uint8Array === 'function') {
      const callback = (c) => {
        const num = Number(c)
        return (num ^ (crypto.getRandomValues(new Uint8Array(1))[0] & (15 >> (num / 4)))).toString(
          16
        )
      }
      return ([1e7] + -1e3 + -4e3 + -8e3 + -1e11).replace(/[018]/g, callback)
    }
  }
  let timestamp = new Date().getTime()
  let perforNow =
    (typeof performance !== 'undefined' && performance.now && performance.now() * 1000) || 0
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    let random = Math.random() * 16
    if (timestamp > 0) {
      random = (timestamp + random) % 16 | 0
      timestamp = Math.floor(timestamp / 16)
    } else {
      random = (perforNow + random) % 16 | 0
      perforNow = Math.floor(perforNow / 16)
    }
    return (c === 'x' ? random : (random & 0x3) | 0x8).toString(16)
  })
}

// 获取动态顶部偏移（根据当前模式是否显示标签栏）
function getTopOffset() {
  const showTabBar = currentMode === 'trading' || currentMode === 'developing'
  return TITLE_BAR_HEIGHT + (showTabBar ? TAB_BAR_HEIGHT : 0)
}

// 获取默认标题
function getDefaultTitle(type) {
  switch (type) {
    case 'chart':
      return '新标签页'
    case 'python':
      return 'Python 编辑器'
    case 'settings':
      return '设置'
    case 'placeholder':
      return '正在开发中'
    default:
      return ''
  }
}

// 创建 WebContentsView（统一创建函数）
function createView(type) {
  const viewId = getUUID()
  const view = new WebContentsView({
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      partition: `persist:${viewId}`,
      preload: join(__dirname, '../preload/index.js')
    }
  })
  view.setBackgroundColor('#2e2c29')
  mainWindow.contentView.addChildView(view)

  const viewData = { view, type, title: getDefaultTitle(type) }
  views.set(viewId, viewData)

  // 初始隐藏
  view.setBounds({ x: ACTIVITY_BAR_WIDTH, y: 0, width: 0, height: 0 })

  // 监听页面标题变化
  view.webContents.on('page-title-updated', (event, title) => {
    viewData.title = title
    mainWindow.webContents.send('tab-title-updated', viewId, title)
  })

  // 监听页面加载状态
  view.webContents.on('did-start-loading', () => {
    mainWindow.webContents.send('tab-loading', viewId, true)
  })
  view.webContents.on('did-stop-loading', () => {
    mainWindow.webContents.send('tab-loading', viewId, false)
  })
  view.webContents.on('did-finish-load', () => {
    mainWindow.webContents.send('tab-loading', viewId, false)
  })
  view.webContents.on('did-fail-load', () => {
    mainWindow.webContents.send('tab-loading', viewId, false)
  })

  // 加载对应页面
  const htmlFileMap = {
    chart: 'chart.html',
    python: 'python.html',
    settings: 'settings.html',
    placeholder: 'placeholder.html'
  }
  const htmlFile = htmlFileMap[type]
  if (htmlFile) {
    if (is.dev && process.env['ELECTRON_RENDERER_URL']) {
      view.webContents.loadURL(`${process.env['ELECTRON_RENDERER_URL']}/${htmlFile}`)
    } else {
      view.webContents.loadFile(join(__dirname, `../renderer/${htmlFile}`))
    }
  }

  return viewId
}

// 在交易模式下创建新的图表标签页
function createNewTab() {
  if (currentMode !== 'trading') return null
  const state = modeState.trading
  if (state.viewIds.size >= 10) {
    mainWindow.webContents.send('tab-limit', '最多只能创建10个标签页')
    return null
  }

  const viewId = createView('chart')
  state.viewIds.add(viewId)

  // 通知渲染进程
  mainWindow.webContents.send('tab-created', viewId)

  setActiveTab(viewId)
  state.activeViewId = viewId
  return viewId
}

// 模式切换
function switchMode(newMode) {
  // 保存当前模式的活动视图
  if (currentMode === 'trading' || currentMode === 'developing') {
    modeState[currentMode].activeViewId = activeViewId
  }

  // 隐藏所有视图
  views.forEach((viewData) => {
    viewData.view.setBounds({ x: ACTIVITY_BAR_WIDTH, y: 0, width: 0, height: 0 })
  })

  currentMode = newMode
  const showTabBar = newMode === 'trading' || newMode === 'developing'
  const showNewTabBtn = newMode === 'trading'

  let tabs = []
  let newActiveViewId = null

  if (newMode === 'trading') {
    const state = modeState.trading
    if (state.viewIds.size === 0) {
      // 首次进入交易模式，创建第一个图表标签页
      const viewId = createView('chart')
      state.viewIds.add(viewId)
      state.activeViewId = viewId
    }
    newActiveViewId = state.activeViewId
    // 构建标签页信息
    state.viewIds.forEach((vid) => {
      const vd = views.get(vid)
      if (vd) tabs.push({ viewId: vid, title: vd.title || '新标签页', type: vd.type })
    })
  } else if (newMode === 'developing') {
    const state = modeState.developing
    if (state.viewIds.size === 0) {
      // 首次进入开发模式，创建 Python 编辑器
      const viewId = createView('python')
      state.viewIds.add(viewId)
      state.activeViewId = viewId
    }
    newActiveViewId = state.activeViewId
    state.viewIds.forEach((vid) => {
      const vd = views.get(vid)
      if (vd) tabs.push({ viewId: vid, title: vd.title || 'Python 编辑器', type: vd.type })
    })
  } else if (newMode === 'news' || newMode === 'market_analyze') {
    const state = modeState[newMode]
    if (!state.viewId) {
      state.viewId = createView('placeholder')
    }
    newActiveViewId = state.viewId
  } else if (newMode === 'settings') {
    const state = modeState.settings
    if (!state.viewId) {
      state.viewId = createView('settings')
    }
    newActiveViewId = state.viewId
  }

  // 显示新模式的活动视图
  if (newActiveViewId) {
    activeViewId = newActiveViewId
    const viewData = views.get(newActiveViewId)
    if (viewData) {
      updateWebViewBounds(mainWindow, viewData.view)
    }
  }

  // 通知渲染进程
  mainWindow.webContents.send('mode-switched', {
    mode: newMode,
    showTabBar,
    showNewTabBtn,
    tabs,
    activeViewId: newActiveViewId
  })
}
// 更新 WebContentsView 边界的函数
function updateWebViewBounds(window, webView) {
  const [mainwin_content_width, mainwin_content_height] = mainWindow.getContentSize()
  const rightPanelWidth = agentPanelVisible ? currentAgentPanelWidth : 0
  const topOffset = getTopOffset()
  webView.setBounds({
    x: ACTIVITY_BAR_WIDTH,
    y: topOffset,
    width: mainwin_content_width - ACTIVITY_BAR_WIDTH - rightPanelWidth,
    height: mainwin_content_height - topOffset
  })
}

// 关闭所有图表页面
function closeAllChartTabs() {
  console.log('[closeAllChartTabs] 开始关闭所有图表页面')
  const state = modeState.trading
  const chartViewIds = Array.from(state.viewIds)

  console.log(`[closeAllChartTabs] 找到 ${chartViewIds.length} 个图表页面需要关闭:`, chartViewIds)

  chartViewIds.forEach((viewId) => {
    const viewData = views.get(viewId)
    if (viewData) {
      console.log(`[closeAllChartTabs] 正在关闭图表页面: ${viewId}`)
      try {
        mainWindow.contentView.removeChildView(viewData.view)
        views.delete(viewId)
        state.viewIds.delete(viewId)
        mainWindow.webContents.send('tab-closed', viewId)
        console.log(`[closeAllChartTabs] 成功关闭图表页面: ${viewId}`)
      } catch (error) {
        console.error(`[closeAllChartTabs] 关闭图表页面失败 ${viewId}:`, error)
      }
    }
  })

  state.activeViewId = null

  // 如果当前在交易模式，创建一个新的图表标签页
  if (currentMode === 'trading') {
    const viewId = createView('chart')
    state.viewIds.add(viewId)
    state.activeViewId = viewId
    mainWindow.webContents.send('tab-created', viewId)
    setActiveTab(viewId)
  }

  console.log(`[closeAllChartTabs] 完成，已关闭 ${chartViewIds.length} 个图表页面`)
}

// 重置可视窗口
function setActiveTab(viewId) {
  views.forEach((viewData, id) => {
    if (id === viewId) {
      updateWebViewBounds(mainWindow, viewData.view)
    } else {
      viewData.view.setBounds({ x: ACTIVITY_BAR_WIDTH, y: 0, width: 0, height: 0 })
    }
  })
  activeViewId = viewId
  // 更新当前模式的活动视图
  if (currentMode === 'trading' || currentMode === 'developing') {
    const state = modeState[currentMode]
    if (state.viewIds.has(viewId)) {
      state.activeViewId = viewId
    }
  }
}

// 监听标签页相关的事件
ipcMain.on('renderer-ready', () => {
  switchMode('trading')
})

ipcMain.on('switch-mode', (event, newMode) => {
  switchMode(newMode)
})

ipcMain.on('new-tab', () => {
  createNewTab()
})

ipcMain.on('switch-tab', (event, viewId) => {
  setActiveTab(viewId)
})

ipcMain.on('close-tab', (event, viewId) => {
  const viewData = views.get(viewId)
  if (!viewData) return

  // 找到该视图所属的模式
  let viewMode = null
  for (const [mode, state] of Object.entries(modeState)) {
    if (state.viewIds && state.viewIds.has(viewId)) {
      viewMode = mode
      break
    }
  }

  // 至少保留1个标签页
  if (viewMode && modeState[viewMode].viewIds.size <= 1) {
    mainWindow.webContents.send('tab-limit', '至少需要保留1个标签页')
    return
  }

  mainWindow.contentView.removeChildView(viewData.view)
  views.delete(viewId)

  if (viewMode && modeState[viewMode].viewIds) {
    modeState[viewMode].viewIds.delete(viewId)
  }

  if (activeViewId === viewId) {
    // 切换到当前模式的最后一个视图
    if (viewMode && modeState[viewMode].viewIds) {
      const remaining = Array.from(modeState[viewMode].viewIds)
      if (remaining.length > 0) {
        setActiveTab(remaining[remaining.length - 1])
      }
    }
  }

  mainWindow.webContents.send('tab-closed', viewId)
})

// 监听关闭所有图表页面的请求
ipcMain.on('close-all-chart-tabs', () => {
  console.log('[IPC] 收到关闭所有图表页面的请求')
  closeAllChartTabs()
})

// 数据源设置的 IPC 处理（解决跨 partition localStorage 隔离问题）
ipcMain.handle('get-data-source', () => {
  return currentDataSource
})

ipcMain.on('set-data-source', (event, dataSource) => {
  console.log('[IPC] 数据源已更新为:', dataSource)
  currentDataSource = dataSource
})

// 监听 Agent 面板切换
ipcMain.on('toggle-agent-panel', (event, visible) => {
  agentPanelVisible = visible
  if (!visible) {
    currentAgentPanelWidth = 0
  } else {
    currentAgentPanelWidth = AGENT_PANEL_WIDTH
  }
  // 更新当前活动视图的尺寸
  if (activeViewId) {
    const activeView = views.get(activeViewId)
    if (activeView) {
      updateWebViewBounds(mainWindow, activeView.view)
    }
  }
})

// 监听 Agent 面板宽度调整
ipcMain.on('resize-agent-panel', (event, width) => {
  currentAgentPanelWidth = width
  if (activeViewId) {
    const activeView = views.get(activeViewId)
    if (activeView) {
      updateWebViewBounds(mainWindow, activeView.view)
    }
  }
})

// 监听右键菜单请求
ipcMain.on('show-context-menu', (event, viewId) => {
  console.log(`open context menu ${viewId}`)
  const viewData = views.get(viewId)
  if (!viewData) return

  const template = [
    {
      label: '打开DevTools',
      click: () => {
        mainWindow.send('context-menu-action', { action: 'copy', viewId: viewId })
        viewData.view.webContents.openDevTools({ mode: 'detach' })
        console.log(`on menu item open DevTools for ${viewId}`)
      }
    },
    {
      label: '粘贴',
      click: () => mainWindow.send('context-menu-action', { action: 'paste', viewId: viewId })
    },
    { type: 'separator' },
    {
      label: '自定义动作',
      click: () => mainWindow.send('context-menu-action', { action: 'custom', viewId: viewId })
    }
  ]
  const menu = Menu.buildFromTemplate(template)
  menu.popup({ window: mainWindow })
})

// // 添加以下函数来广播消息给所有标签
// function broadcastToAllTabs(channel, ...args) {
//   views.forEach((view) => {
//     view.webContents.send(channel, ...args)
//   })
// }



// app.whenReady().then(createWindow)

// This method will be called when Electron has finished
// initialization and is ready to create browser windows.
// Some APIs can only be used after this event occurs.
app.whenReady().then(() => {
  // Set app user model id for windows
  electronApp.setAppUserModelId('com.electron')

  // 为所有新创建的 session 设置 CORS 旁路（解决 OKX API 不返回 CORS 头的问题）
  app.on('session-created', (newSession) => {
    newSession.webRequest.onHeadersReceived((details, callback) => {
      const { responseHeaders } = details
      if (details.url.includes('okx.com')) {
        responseHeaders['Access-Control-Allow-Origin'] = ['*']
        responseHeaders['Access-Control-Allow-Methods'] = ['GET, POST, OPTIONS']
        responseHeaders['Access-Control-Allow-Headers'] = ['*']
      }
      callback({ responseHeaders })
    })
  })

  // 也为默认 session 设置
  session.defaultSession.webRequest.onHeadersReceived((details, callback) => {
    const { responseHeaders } = details
    if (details.url.includes('okx.com')) {
      responseHeaders['Access-Control-Allow-Origin'] = ['*']
      responseHeaders['Access-Control-Allow-Methods'] = ['GET, POST, OPTIONS']
      responseHeaders['Access-Control-Allow-Headers'] = ['*']
    }
    callback({ responseHeaders })
  })

  // Default open or close DevTools by F12 in development
  // and ignore CommandOrControl + R in production.
  // see https://github.com/alex8088/electron-toolkit/tree/master/packages/utils
  app.on('browser-window-created', (_, window) => {
    optimizer.watchWindowShortcuts(window)
  })

  // IPC test
  ipcMain.on('ping', () => console.log('pong'))

  createWindow()

  app.on('activate', function () {
    // On macOS it's common to re-create a window in the app when the
    // dock icon is clicked and there are no other windows open.
    if (BrowserWindow.getAllWindows().length === 0) createWindow()
  })
})

// Quit when all windows are closed, except on macOS. There, it's common
// for applications and their menu bar to stay active until the user quits
// explicitly with Cmd + Q.
app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit()
  }
})

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow()
  }
})
// In this file you can include the rest of your app's specific main process
// code. You can also put them in separate files and require them here.

ipcMain.on('open-dev-tools-in-new-window', (event) => {
  // const mainWindow = BrowserWindow.fromWebContents(event.sender)
  const devToolsWindow = new BrowserWindow({ width: 800, height: 600, title: 'DevTool' })

  // 将 DevTools 从主窗口移动到新窗口
  mainWindow.webContents.devToolsWebContents.executeJavaScript(`
      InspectorFrontendHost.setInspectedWindowTab(null);
      InspectorFrontendHost.showWindow();
  `)
  mainWindow.webContents.devToolsWebContents.setDevToolsWebContents(devToolsWindow.webContents)

  const mainPos = mainWindow.getPosition()
  devToolsWindow.setPosition(mainPos[0] + mainWindow.getSize()[0] + 10, mainPos[1])

  devToolsWindow.focus()
})
