import { app, shell, WebContentsView, BrowserWindow, ipcMain } from 'electron'
import { join } from 'path'
import { is, electronApp, optimizer } from '@electron-toolkit/utils'
import icon from '../../resources/icon.png?asset'

// 全局的变量参数
let mainWindow // 主进程的唯一窗口，所有tab都被它加载
let views = new Map() // 所有的view 对象
let activeViewId = null // 活动的view对象
let homeViewId // home的viewId

function createWindow() {
  // Create the browser window.
  mainWindow = new BrowserWindow({
    width: 1600,
    height: 1000,
    show: false,
    title: 'Prophet-Next',
    autoHideMenuBar: false,
    ...(process.platform === 'linux' ? { icon } : {}),
    webPreferences: {
      preload: join(__dirname, '../preload/index.js'),
      sandbox: false
    }
  })

  mainWindow.on('ready-to-show', () => {
    mainWindow.show()
  })

  mainWindow.webContents.setWindowOpenHandler((details) => {
    shell.openExternal(details.url)
    return { action: 'deny' }
  })

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

// 创建 HomeTab
function createHomeTab() {
  const viewId = getUUID() // Date.now().toString()
  const view = new WebContentsView({
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      partition: `persist:${viewId}`, // 实现存储隔离
      preload: join(__dirname, '../preload/index.js') // 添加 preload 脚本
    }
  })

  updateWebViewBounds(mainWindow, view)
  mainWindow.contentView.addChildView(view)
  views.set(viewId, view)
  // 监听窗口移动事件（如果需要）
  mainWindow.on('move', () => {
    updateWebViewBounds(mainWindow, view)
  })

  // 监听窗口大小变化事件
  mainWindow.on('resize', () => {
    updateWebViewBounds(mainWindow, view)
  })

  // 视图的边界
  const [width, height] = mainWindow.getContentSize()
  view.setBounds({ x: 0, y: 40, width, height: height - 40 })

  // 发送新标签页信息给渲染进程
  mainWindow.webContents.send('home-created', viewId)

  // 监听页面标题变化
  view.webContents.on('page-title-updated', (event, title) => {
    mainWindow.webContents.send('tab-title-updated', viewId, title)
  })

  // 监听页面加载状态
  view.webContents.on('did-start-loading', () => {
    mainWindow.webContents.send('tab-loading', viewId, true)
  })

  view.webContents.on('did-stop-loading', () => {
    mainWindow.webContents.send('tab-loading', viewId, false)
  })

  // 添加导航完成事件监听，确保页面完全加载后移除加载状态
  view.webContents.on('did-finish-load', () => {
    mainWindow.webContents.send('tab-loading', viewId, false)
  })

  // 添加加载失败事件监听
  view.webContents.on('did-fail-load', () => {
    mainWindow.webContents.send('tab-loading', viewId, false)
  })

  // home页面
  view.webContents.loadURL(join(__dirname, '../renderer/home.html'))
  view.webContents.openDevTools({ mode: 'detach' }); // 'detach' 模式使工具窗口独立ssss

  setActiveTab(viewId)
  homeViewId = viewId
  return viewId
}

// 创建一个tab
function createNewTab() {
  // 如果已经有10个标签，则不再创建
  if (views.size >= 10) {
    // 通知渲染进程显示提示
    mainWindow.webContents.send('tab-limit', '最多只能创建10个标签页')
    return null
  }

  const viewId = getUUID() // Date.now().toString()
  const view = new WebContentsView({
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      partition: `persist:${viewId}`, // 实现存储隔离
      preload: join(__dirname, '../preload/index.js') // 添加 preload 脚本
    }
  })

  updateWebViewBounds(mainWindow, view)
  mainWindow.contentView.addChildView(view)
  views.set(viewId, view)
  // 监听窗口移动事件（如果需要）
  mainWindow.on('move', () => {
    updateWebViewBounds(mainWindow, view)
  })

  // 监听窗口大小变化事件
  mainWindow.on('resize', () => {
    updateWebViewBounds(mainWindow, view)
  })

  // 视图的边界
  const [width, height] = mainWindow.getContentSize()
  view.setBounds({ x: 0, y: 40, width, height: height - 40 })

  // 发送新标签页信息给渲染进程
  mainWindow.webContents.send('tab-created', viewId)

  // 监听页面标题变化
  view.webContents.on('page-title-updated', (event, title) => {
    mainWindow.webContents.send('tab-title-updated', viewId, title)
  })

  // 监听页面加载状态
  view.webContents.on('did-start-loading', () => {
    mainWindow.webContents.send('tab-loading', viewId, true)
  })

  view.webContents.on('did-stop-loading', () => {
    mainWindow.webContents.send('tab-loading', viewId, false)
  })

  // 添加导航完成事件监听，确保页面完全加载后移除加载状态
  view.webContents.on('did-finish-load', () => {
    mainWindow.webContents.send('tab-loading', viewId, false)
  })

  // 添加加载失败事件监听
  view.webContents.on('did-fail-load', () => {
    mainWindow.webContents.send('tab-loading', viewId, false)
  })

  if (!app.isPackaged && process.env['ELECTRON_RENDERER_URL']) {
    view.webContents.loadURL(`${process.env['ELECTRON_RENDERER_URL']}/chart.html`)
  } else {
    view.webContents.loadFile(join(__dirname, '../renderer/chart.html'))
  }

  // view.webContents.loadURL(join(__dirname, '../renderer/chart.html'))
  
  view.webContents.openDevTools({ mode: 'detach' }); // 'detach' 模式使工具窗口独立ssss

  setActiveTab(viewId)
  return viewId
}

// 更新 WebContentsView 边界的函数
function updateWebViewBounds(window, webView) {
  // 设置 WebContentsView 填充整个内容区域
  webView.setBounds({
    x: 0,
    y: 40,
    width: window.getBounds().width - 10,
    height: window.getBounds().height - 20
  })

  // 可选：设置缩放因子以适应内容
  // webView.webContents.setZoomFactor(0.95)
}

// 重置可视窗口
function setActiveTab(viewId) {
  views.forEach((view, id) => {
    if (id === viewId) {
      updateWebViewBounds(mainWindow, view)
      // view.setBounds({
      //   x: 0,
      //   y: 40,
      //   width: mainWindow.getBounds().width,
      //   height: mainWindow.getBounds().height - 40
      // })
    } else {
      view.setBounds({ x: 0, y: 40, width: 0, height: 0 })
    }
  })
  activeViewId = viewId
}

// 监听标签页相关的事件
ipcMain.on('home-tab', () => {
  createHomeTab()
})

ipcMain.on('new-tab', () => {
  createNewTab()
})

ipcMain.on('switch-tab', (event, viewId) => {
  setActiveTab(viewId)
})

ipcMain.on('close-tab', (event, viewId) => {
  const view = views.get(viewId)
  // 修改判断条件，添加标签数量检查
  if (view && views.size > 1) {
    // mainWindow.removeBrowserView(view)
    mainWindow.contentView.removeChildView(view)
    views.delete(viewId)

    if (activeViewId === viewId) {
      const lastViewId = Array.from(views.keys())[views.size - 1]
      setActiveTab(lastViewId)
    }

    mainWindow.webContents.send('tab-closed', viewId)
  } else {
    // 通知渲染进程显示提示
    mainWindow.webContents.send('tab-limit', '至少需要保留1个标签页')
  }
})

// 添加以下函数来广播消息给所有标签
function broadcastToAllTabs(channel, ...args) {
  views.forEach((view) => {
    view.webContents.send(channel, ...args)
  })
}

// 示例：主进程向所有标签发送消息
ipcMain.on('message-from-tab', (event, message) => {
  // 获取发送消息的标签ID
  const sender = event.sender
  const senderView = Array.from(views.entries()).find(
    // eslint-disable-next-line no-unused-vars
    ([_, view]) => view.webContents.id === sender.id
  )

  if (senderView) {
    const [viewId] = senderView
    // 只回复发送消息的标签
    sender.send('message-response', `回复标签 ${viewId}: 收到消息 "${message}"`)

    // 向所有标签广播通知
    broadcastToAllTabs('broadcast-message', `标签 ${viewId} 发送了消息: "${message}"`)
  }
})

// app.whenReady().then(createWindow)

// This method will be called when Electron has finished
// initialization and is ready to create browser windows.
// Some APIs can only be used after this event occurs.
app.whenReady().then(() => {
  // Set app user model id for windows
  electronApp.setAppUserModelId('com.electron')

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
