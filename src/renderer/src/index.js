const tabsContainer = document.getElementById('tabs')
const newTabBtn = document.getElementById('new-tab-btn')
const sidebarTradingBtn = document.getElementById('sidebar-trading-btn')
const sidebarDevelopingBtn = document.getElementById('sidebar-developing-btn')
const sidebarNewsBtn = document.getElementById('sidebar-news-btn')
const sidebarMarketBtn = document.getElementById('sidebar-market-btn')
const sidebarSettingsBtn = document.getElementById('sidebar-settings-btn')
const tabsScroll = document.querySelector('.tabs-scroll')
const scrollLeftBtn = document.getElementById('scroll-left')
const scrollRightBtn = document.getElementById('scroll-right')
const toggleAgentBtn = document.getElementById('toggle-agent-btn')
const agentPanel = document.getElementById('agent-panel')
const agentInput = document.getElementById('agent-input')
const tabsContainerEl = document.querySelector('.tabs-container')
let activeTabId = null
let tabCounter = 0 // 用于跟踪标签序号
// 添加一个 Map 来跟踪每个标签页的加载状态
const loadingStates = new Map()
let tabDragJustEnded = false

// 模式管理
let currentMode = 'trading'
const modeViews = {
  trading: new Set(),
  developing: new Set()
}
// 保存每个模式的标签页 DOM 状态
const modeSavedTabs = {
  trading: { elements: [], activeTabId: null },
  developing: { elements: [], activeTabId: null }
}

// 获取当前模式的 views
function getCurrentModeViews() {
  return modeViews[currentMode] || new Set()
}

// Suppress tab click right after drag ends
tabsContainer.addEventListener(
  'click',
  (e) => {
    if (tabDragJustEnded && e.target.closest('.tab')) {
      e.stopPropagation()
    }
  },
  true
)

// 创建标签页元素（统一函数）
function createTabElement(viewId, title) {
  const tab = document.createElement('div')
  tab.className = 'tab'
  tab.setAttribute('data-view-id', viewId)

  tabCounter++
  const displayTitle = title || `新标签页 ${tabCounter}`
  tab.innerHTML = `
    <span class="tab-title">${displayTitle}</span>
    <span class="close-btn">×</span>
    <div class="tab-loading"></div>
  `

  // 初始化加载状态
  loadingStates.set(viewId, false)

  // 点击标签页，激活当前页面
  tab.addEventListener('click', () => {
    setActiveTab(viewId)
    window.electronAPI.switchTab(viewId)
  })

  // 点击关闭按钮
  const closeBtn = tab.querySelector('.close-btn')
  closeBtn.addEventListener('click', (e) => {
    e.stopPropagation()
    const currentViews = getCurrentModeViews()
    if (currentViews.size > 1) {
      window.electronAPI.closeTab(viewId)
    } else {
      showToast('至少需要保留1个标签页')
    }
  })

  // 右键菜单
  tab.addEventListener('contextmenu', (e) => {
    e.preventDefault()
    window.electronAPI.openContextMenu(viewId)
    window.selectedElement = e.target
  })

  setupTabDrag(tab)
  return tab
}

// 将viewId设为焦点
function setActiveTab(viewId) {
  document.querySelectorAll('.tab').forEach((tab) => {
    tab.classList.remove('active')
    if (tab.getAttribute('data-view-id') === viewId) {
      tab.classList.add('active')
      tab.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'nearest' })
    }
  })
  activeTabId = viewId
  updateScrollButtons()
}

// 按 新页面 按钮（仅交易模式下有效）
newTabBtn.addEventListener('click', () => {
  const currentViews = getCurrentModeViews()
  if (currentViews.size < 10) {
    window.electronAPI.createNewTab()
  } else {
    showToast('最多只能创建10个标签页')
  }
})

// 侧边栏: 模式切换按钮
sidebarTradingBtn.addEventListener('click', () => {
  window.electronAPI.switchMode('trading')
})

sidebarDevelopingBtn.addEventListener('click', () => {
  window.electronAPI.switchMode('developing')
})

sidebarNewsBtn.addEventListener('click', () => {
  window.electronAPI.switchMode('news')
})

sidebarMarketBtn.addEventListener('click', () => {
  window.electronAPI.switchMode('market_analyze')
})

sidebarSettingsBtn.addEventListener('click', () => {
  window.electronAPI.switchMode('settings')
})

// 响应模式切换
window.electronAPI.onModeSwitched((data) => {
  const oldMode = currentMode

  // 保存旧模式的标签页 DOM 状态
  if (oldMode === 'trading' || oldMode === 'developing') {
    const tabElements = Array.from(tabsContainer.querySelectorAll('.tab'))
    modeSavedTabs[oldMode] = {
      elements: tabElements,
      activeTabId: activeTabId
    }
    // 从 DOM 中移除（但保留在内存中）
    tabElements.forEach((tab) => tab.remove())
  }

  currentMode = data.mode

  // 显示/隐藏标签栏
  tabsContainerEl.style.display = data.showTabBar ? 'flex' : 'none'

  // 显示/隐藏新建按钮
  newTabBtn.style.display = data.showNewTabBtn ? 'flex' : 'none'

  // 恢复新模式的标签页
  if (data.showTabBar) {
    const saved = modeSavedTabs[data.mode]
    if (saved && saved.elements.length > 0) {
      // 恢复之前保存的标签页 DOM 元素（带有事件监听器）
      saved.elements.forEach((tab) => tabsContainer.insertBefore(tab, newTabBtn))
      if (saved.activeTabId) {
        setActiveTab(saved.activeTabId)
        window.electronAPI.switchTab(saved.activeTabId)
      }
      // 清空已恢复的保存状态
      modeSavedTabs[data.mode] = { elements: [], activeTabId: null }
    } else if (data.tabs && data.tabs.length > 0) {
      // 首次进入此模式，从主进程数据创建标签页
      if (!modeViews[data.mode]) modeViews[data.mode] = new Set()
      data.tabs.forEach((tabInfo) => {
        modeViews[data.mode].add(tabInfo.viewId)
        const tab = createTabElement(tabInfo.viewId, tabInfo.title)
        tabsContainer.insertBefore(tab, newTabBtn)
      })
      if (data.activeViewId) {
        setActiveTab(data.activeViewId)
      }
    }
    updateNewTabButtonVisibility()
  }

  // 更新侧边栏激活状态
  updateSidebarActiveState(data.mode)

  setTimeout(updateScrollButtons, 0)
})

// 响应标签页创建（在当前模式下新建标签页）
window.electronAPI.onTabCreated((event, viewId) => {
  const currentViews = getCurrentModeViews()
  currentViews.add(viewId)
  const tab = createTabElement(viewId)

  // 将新标签插入到新建按钮之前
  tabsContainer.insertBefore(tab, newTabBtn)

  setActiveTab(viewId)
  window.electronAPI.switchTab(viewId)
  updateNewTabButtonVisibility()
  setTimeout(updateScrollButtons, 0)
})

window.electronAPI.onTabClosed((event, viewId) => {
  // 从所有模式的 views 中移除
  Object.values(modeViews).forEach((viewSet) => viewSet.delete(viewId))
  loadingStates.delete(viewId)
  const tab = document.querySelector(`[data-view-id="${viewId}"]`)
  if (tab) {
    tab.remove()
    updateTabNumbers()
    updateNewTabButtonVisibility()
  }
  setTimeout(updateScrollButtons, 0)
})

window.electronAPI.onTabLimit((message) => {
  showToast(message)
})

window.addEventListener('beforeunload', () => {
  window.electronAPI.removeAllListeners()
})

// 初始化时通知主进程渲染进程已就绪，请求创建首页
// 检测平台并添加对应 CSS 类
if (window.electronAPI && window.electronAPI.getPlatform) {
  const platform = window.electronAPI.getPlatform()
  document.body.classList.add(`platform-${platform}`)
}

window.electronAPI.rendererReady()

updateNewTabButtonVisibility()

function updateScrollButtons() {
  const { scrollLeft, scrollWidth, clientWidth } = tabsScroll
  const hasOverflow = scrollWidth > clientWidth

  // 只在有溢出内容时显示滚动按钮
  if (!hasOverflow) {
    scrollLeftBtn.style.display = 'none'
    scrollRightBtn.style.display = 'none'
    return
  }

  // 根据滚动位置显示/隐藏对应的按钮
  scrollLeftBtn.style.display = scrollLeft > 0 ? 'flex' : 'none'
  scrollRightBtn.style.display = Math.ceil(scrollLeft + clientWidth) < scrollWidth ? 'flex' : 'none'
}

scrollLeftBtn.addEventListener('click', () => {
  tabsScroll.scrollBy({ left: -200, behavior: 'smooth' })
})

scrollRightBtn.addEventListener('click', () => {
  tabsScroll.scrollBy({ left: 200, behavior: 'smooth' })
})

tabsScroll.addEventListener('scroll', updateScrollButtons)

window.addEventListener('resize', () => {
  requestAnimationFrame(updateScrollButtons)
})

// 在标签内容变化时更新滚动按钮状态
const observer = new MutationObserver(() => {
  requestAnimationFrame(updateScrollButtons)
})

observer.observe(tabsContainer, {
  childList: true,
  subtree: true
})

// 更新标签序号
function updateTabNumbers() {
  document.querySelectorAll('.tab').forEach((tab, index) => {
    const titleElement = tab.querySelector('.tab-title')
    if (titleElement) {
      const currentTitle = titleElement.textContent
      const tabNumber = index + 1

      // 如果是默认标题，只更新序号
      if (currentTitle.startsWith('新标签页')) {
        titleElement.textContent = `新标签页 ${tabNumber}`
      }
      // } else {
      //   // 更新带有网站标题的序号
      //   const match = currentTitle.match(/(.*?)\s*\(\d+\)$/)
      //   const baseTitle = match ? match[1] : currentTitle
      //   titleElement.textContent = `${baseTitle} (${tabNumber})`
      // }
    }
  })
  tabCounter = document.querySelectorAll('.tab').length
}

// 更新新建按钮显示状态
function updateNewTabButtonVisibility() {
  if (currentMode !== 'trading') {
    newTabBtn.style.display = 'none'
    return
  }
  const currentViews = getCurrentModeViews()
  newTabBtn.style.display = currentViews.size >= 10 ? 'none' : 'flex'
}

// 修改加载状态处理函数
window.electronAPI.onTabLoading((viewId, isLoading) => {
  const tab = document.querySelector(`[data-view-id="${viewId}"]`)
  if (!tab) return

  const loadingBar = tab.querySelector('.tab-loading')
  if (!loadingBar) return

  // 更新加载状态
  loadingStates.set(viewId, isLoading)

  if (isLoading) {
    loadingBar.classList.add('active')
  } else {
    // 添加一个小延迟确保动画平滑
    setTimeout(() => {
      // 再次检查状态，确保没有新的加载开始
      if (!loadingStates.get(viewId)) {
        loadingBar.classList.remove('active')
      }
    }, 200)
  }
})

// 添加标题更新处理
window.electronAPI.onTabTitleUpdated((event, viewId, title) => {
  console.log('[index.js] onTabTitleUpdated called:', {
    event,
    viewId,
    title,
    viewIdType: typeof viewId
  })

  // 确保 viewId 是字符串（因为 data-view-id 属性是字符串）
  const viewIdStr = String(viewId)

  // 列出所有现有的标签页，用于调试
  const allTabs = document.querySelectorAll('.tab')
  const allViewIds = Array.from(allTabs).map((tab) => tab.getAttribute('data-view-id'))
  console.log('[index.js] All existing viewIds:', allViewIds)
  console.log('[index.js] Looking for viewId:', viewIdStr)

  const updateTabTitle = (tabElement) => {
    const titleElement = tabElement.querySelector('.tab-title')
    if (!titleElement) {
      console.warn('[index.js] Title element not found for viewId:', viewIdStr)
      return false
    }

    // 如果标题为空或是默认标题，显示默认标题
    if (!title || title === 'about:blank' || title.trim() === '') {
      const tabNumber = Array.from(document.querySelectorAll('.tab')).indexOf(tabElement) + 1
      titleElement.textContent = `新标签页 ${tabNumber}`
      console.log('[index.js] Title is empty, using default:', titleElement.textContent)
      return true
    }

    // 清理标题：移除 "- Chart" 后缀（如果存在）
    let cleanTitle = title.replace(/\s*-\s*Chart\s*$/i, '').trim()

    // 如果清理后标题为空，使用默认标题
    if (!cleanTitle) {
      const tabNumber = Array.from(document.querySelectorAll('.tab')).indexOf(tabElement) + 1
      titleElement.textContent = `新标签页 ${tabNumber}`
      console.log('[index.js] Cleaned title is empty, using default:', titleElement.textContent)
      return true
    }

    console.log('[index.js] Processing title:', cleanTitle, 'for viewId:', viewIdStr)

    // 获取所有其他标签页的标题（排除当前标签页）
    const allTabs = document.querySelectorAll('.tab')
    const otherTitles = Array.from(allTabs)
      .map((tab) => {
        const tabViewId = tab.getAttribute('data-view-id')
        // 排除当前标签页
        if (tabViewId === viewIdStr) return null
        const titleEl = tab.querySelector('.tab-title')
        return titleEl ? titleEl.textContent.trim() : null
      })
      .filter((t) => t && t && !t.startsWith('新标签页'))

    console.log('[index.js] Other titles:', otherTitles)

    // 检查是否有同名标题（基础标题相同，可能带有 -2, -3 等后缀）
    const baseTitle = cleanTitle
    const sameTitleTabs = otherTitles.filter((t) => {
      if (!t) return false
      // 提取基础标题（移除后缀）
      const otherBaseTitle = t.replace(/-\d+$/, '')
      return otherBaseTitle === baseTitle
    })

    console.log('[index.js] Same title tabs:', sameTitleTabs)

    // 如果有同名标题，添加序号后缀
    if (sameTitleTabs.length > 0) {
      // 找到最大的序号
      let maxSuffix = 0
      sameTitleTabs.forEach((t) => {
        if (t === baseTitle) {
          // 如果没有后缀，说明是第一个同名标题
          maxSuffix = Math.max(maxSuffix, 1)
        } else {
          // 提取后缀数字
          const match = t.match(/-(\d+)$/)
          if (match) {
            const suffix = parseInt(match[1], 10)
            maxSuffix = Math.max(maxSuffix, suffix)
          }
        }
      })
      // 当前标签页使用下一个序号
      cleanTitle = `${baseTitle}-${maxSuffix + 1}`
      console.log('[index.js] Found same titles, using suffix:', cleanTitle)
    } else {
      console.log('[index.js] No same titles, using base title:', cleanTitle)
    }

    titleElement.textContent = cleanTitle
    console.log('[index.js] Title updated successfully:', cleanTitle)
    return true
  }

  const tab = document.querySelector(`[data-view-id="${viewIdStr}"]`)
  if (!tab) {
    console.warn('[index.js] Tab not found for viewId:', viewIdStr)
    console.warn('[index.js] Available viewIds:', allViewIds)
    // 尝试延迟重试（可能标签页还在创建中）
    setTimeout(() => {
      const retryTab = document.querySelector(`[data-view-id="${viewIdStr}"]`)
      if (retryTab) {
        console.log('[index.js] Tab found on retry, updating title')
        updateTabTitle(retryTab)
      } else {
        console.warn('[index.js] Tab still not found after retry')
      }
    }, 100)
    return
  }

  updateTabTitle(tab)
})

window.electronAPI.onContextMenuPushed((data) => {
  // const element = window.selectedElement
  const viewId = data.viewId
  const action = data.action
  console.info(`onContextMenuPushed ${viewId}`)
  switch (action) {
    case 'copy':
      console.log(`复制操作 ${viewId}`)
      // 执行复制逻辑
      break
    case 'paste':
      console.log(`粘贴操作 ${viewId}`)
      // 执行粘贴逻辑
      break
    case 'custom':
      console.log(`自定义操作 ${viewId}`)
      // 自定义业务逻辑
      break
    default:
      console.log(`hello ${action} ${viewId}`)
      break
  }
})

// 监听菜单操作反馈
window.addEventListener('keydown', (e) => {
  // 检测 Ctrl+Shift+I / Cmd+Option+I
  if ((e.ctrlKey && e.shiftKey && e.key === 'I') || (e.metaKey && e.altKey && e.key === 'I')) {
    e.preventDefault()
    window.electronAPI.openDevTools()
    console.log('open-dev-tools-in-new-window for Ctrl+Shift+I')
  }

  // 检测 F12
  if (e.key === 'F12') {
    e.preventDefault()
    window.electronAPI.openDevTools()
  }
})

// =====================
// Tab Drag Reordering
// =====================
let dragState = null

function setupTabDrag(tabEl) {
  tabEl.addEventListener('dragstart', (e) => e.preventDefault())

  tabEl.addEventListener('mousedown', (e) => {
    if (e.button !== 0) return
    if (e.target.closest('.close-btn')) return
    e.preventDefault()

    // Clean up any stale drag state
    if (dragState) {
      dragState.allTabs.forEach((t) => {
        t.style.transition = ''
        t.style.transform = ''
      })
      dragState.tab.classList.remove('dragging')
      document.body.style.cursor = ''
      document.body.style.userSelect = ''
      dragState = null
    }

    const startX = e.clientX

    const onMouseMove = (moveEvt) => {
      const dx = moveEvt.clientX - startX

      if (!dragState) {
        if (Math.abs(dx) < 5) return

        const allTabs = [...tabsContainer.querySelectorAll('.tab')]
        if (allTabs.length < 2) return
        const rects = allTabs.map((t) => t.getBoundingClientRect())
        const idx = allTabs.indexOf(tabEl)

        // Compute slot width from actual tab positions
        let slotWidth
        if (idx < allTabs.length - 1) {
          slotWidth = rects[idx + 1].left - rects[idx].left
        } else if (idx > 0) {
          slotWidth = rects[idx].left - rects[idx - 1].left
        } else {
          slotWidth = rects[idx].width
        }

        dragState = {
          tab: tabEl,
          allTabs,
          rects,
          originalIndex: idx,
          currentIndex: idx,
          slotWidth
        }

        tabEl.classList.add('dragging')
        document.body.style.cursor = 'grabbing'
        document.body.style.userSelect = 'none'

        // Smooth transition on sibling tabs
        allTabs.forEach((t, i) => {
          if (i !== idx) {
            t.style.transition = 'transform 200ms ease'
          }
        })
      }

      // Move dragged tab with cursor
      tabEl.style.transform = `translateX(${dx}px)`

      // Current center of the dragged tab (based on original position)
      const origRect = dragState.rects[dragState.originalIndex]
      const currentCenter = origRect.left + origRect.width / 2 + dx

      // Determine target index
      let target = dragState.originalIndex
      for (let i = 0; i < dragState.rects.length; i++) {
        if (i === dragState.originalIndex) continue
        const rCenter = dragState.rects[i].left + dragState.rects[i].width / 2
        if (i < dragState.originalIndex && currentCenter < rCenter) {
          target = Math.min(target, i)
        }
        if (i > dragState.originalIndex && currentCenter > rCenter) {
          target = Math.max(target, i)
        }
      }

      // Shift siblings to make room
      if (target !== dragState.currentIndex) {
        dragState.currentIndex = target
        const { originalIndex, allTabs: tabs, slotWidth: sw } = dragState

        tabs.forEach((t, i) => {
          if (i === originalIndex) return
          if (originalIndex < target && i > originalIndex && i <= target) {
            t.style.transform = `translateX(${-sw}px)`
          } else if (originalIndex > target && i >= target && i < originalIndex) {
            t.style.transform = `translateX(${sw}px)`
          } else {
            t.style.transform = 'translateX(0px)'
          }
        })
      }
    }

    const onMouseUp = () => {
      document.removeEventListener('mousemove', onMouseMove)
      document.removeEventListener('mouseup', onMouseUp)

      if (!dragState) return

      const { tab: draggedTab, allTabs, originalIndex, currentIndex } = dragState

      // Clean up styles
      allTabs.forEach((t) => {
        t.style.transition = ''
        t.style.transform = ''
      })
      draggedTab.classList.remove('dragging')
      document.body.style.cursor = ''
      document.body.style.userSelect = ''

      // Reorder DOM if position changed
      if (currentIndex !== originalIndex) {
        const newTabBtnEl = document.getElementById('new-tab-btn')
        draggedTab.remove()
        const remainingTabs = [...tabsContainer.querySelectorAll('.tab')]

        if (currentIndex >= remainingTabs.length) {
          tabsContainer.insertBefore(draggedTab, newTabBtnEl)
        } else {
          tabsContainer.insertBefore(draggedTab, remainingTabs[currentIndex])
        }
        updateTabNumbers()
      }

      // Suppress click event after drag
      tabDragJustEnded = true
      requestAnimationFrame(() => {
        tabDragJustEnded = false
      })
      dragState = null
    }

    document.addEventListener('mousemove', onMouseMove)
    document.addEventListener('mouseup', onMouseUp)
  })
}

// =====================
// Sidebar Active State
// =====================
function updateSidebarActiveState(mode) {
  // 清除所有 active
  document.querySelectorAll('.activity-bar-item').forEach((item) => {
    item.classList.remove('active')
  })
  // 根据模式激活对应图标
  switch (mode) {
    case 'trading':
      sidebarTradingBtn.classList.add('active')
      break
    case 'developing':
      sidebarDevelopingBtn.classList.add('active')
      break
    case 'news':
      sidebarNewsBtn.classList.add('active')
      break
    case 'market_analyze':
      sidebarMarketBtn.classList.add('active')
      break
    case 'settings':
      sidebarSettingsBtn.classList.add('active')
      break
  }
}

// =====================
// Agent 侧栏切换
// =====================
let agentPanelVisible = true

toggleAgentBtn.addEventListener('click', () => {
  agentPanelVisible = !agentPanelVisible
  agentPanel.classList.toggle('hidden', !agentPanelVisible)
  toggleAgentBtn.classList.toggle('active', agentPanelVisible)
  // 通知主进程更新 view 尺寸
  window.electronAPI.toggleAgentPanel(agentPanelVisible)
})

// 自动调整 textarea 高度
agentInput.addEventListener('input', () => {
  agentInput.style.height = 'auto'
  agentInput.style.height = Math.min(agentInput.scrollHeight, 120) + 'px'
})

// =====================
// Agent 侧栏拖拽调整宽度
// =====================
const agentResizeHandle = document.getElementById('agent-resize-handle')
let isResizing = false

agentResizeHandle.addEventListener('mousedown', (e) => {
  if (!agentPanelVisible) return
  e.preventDefault()
  isResizing = true
  agentResizeHandle.classList.add('dragging')
  document.body.style.cursor = 'col-resize'
  document.body.style.userSelect = 'none'

  const onMouseMove = (moveEvt) => {
    const containerRight = document.querySelector('.workspace-row').getBoundingClientRect().right
    let newWidth = containerRight - moveEvt.clientX
    newWidth = Math.max(200, Math.min(600, newWidth))
    agentPanel.style.width = newWidth + 'px'
    // 通知主进程更新 view 尺寸
    window.electronAPI.resizeAgentPanel(newWidth)
  }

  const onMouseUp = () => {
    isResizing = false
    agentResizeHandle.classList.remove('dragging')
    document.body.style.cursor = ''
    document.body.style.userSelect = ''
    document.removeEventListener('mousemove', onMouseMove)
    document.removeEventListener('mouseup', onMouseUp)
  }

  document.addEventListener('mousemove', onMouseMove)
  document.addEventListener('mouseup', onMouseUp)
})
