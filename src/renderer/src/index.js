const tabsContainer = document.getElementById('tabs')
const newTabBtn = document.getElementById('new-tab-btn')
const homeBtn = document.getElementById('home-btn')
const settingsBtn = document.getElementById('settings-btn')
const hashBtn = document.getElementById('hash-btn')
const tabsScroll = document.querySelector('.tabs-scroll')
const scrollLeftBtn = document.getElementById('scroll-left')
const scrollRightBtn = document.getElementById('scroll-right')
let activeTabId = null
let views = new Set() // 用于跟踪标签数量
let tabCounter = 0 // 用于跟踪标签序号
let homeViewId
// 添加一个 Map 来跟踪每个标签页的加载状态
const loadingStates = new Map()

// 创建主页tab
function createHomeElement(viewId) {
  const tab = document.createElement('div')
  tab.className = 'tab'
  tab.setAttribute('data-view-id', viewId)

  tabCounter++

  tab.innerHTML = `
    <span class="tab-title">Home</span>
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
    console.log(`close-btn pushed`)
    e.stopPropagation()
    if (views.size > 1) {
      // 只有当标签数量大于1时才允许关闭
      window.electronAPI.closeTab(viewId)
    } else {
      showToast('至少需要保留1个标签页')
    }
  })
  // 右键菜单
  tab.addEventListener('contextmenu', (e) => {
    e.preventDefault() // 阻止默认右键菜单
    // 可在此处传递元素信息（如ID）
    window.electronAPI.openContextMenu(viewId)
    // 保存事件目标（可选）
    window.selectedElement = e.target
  })

  return tab
}

// 创建设置tab
function createSettingsElement(viewId) {
  const tab = document.createElement('div')
  tab.className = 'tab'
  tab.setAttribute('data-view-id', viewId)

  tabCounter++

  tab.innerHTML = `
    <span class="tab-title">设置</span>
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
    console.log(`close-btn pushed`)
    e.stopPropagation()
    if (views.size > 1) {
      // 只有当标签数量大于1时才允许关闭
      window.electronAPI.closeTab(viewId)
    } else {
      showToast('至少需要保留1个标签页')
    }
  })
  // 右键菜单
  tab.addEventListener('contextmenu', (e) => {
    e.preventDefault() // 阻止默认右键菜单
    // 可在此处传递元素信息（如ID）
    window.electronAPI.openContextMenu(viewId)
    // 保存事件目标（可选）
    window.selectedElement = e.target
  })

  return tab
}

// 创建非主页tab
function createTabElement(viewId) {
  const tab = document.createElement('div')
  tab.className = 'tab'
  tab.setAttribute('data-view-id', viewId)

  tabCounter++
  const tabNumber = tabCounter // 保存当前标签的序号
  tab.innerHTML = `
    <span class="tab-title">新标签页 ${tabNumber}</span>
    <span class="close-btn">×</span>
    <div class="tab-loading"></div>
  `

  // 初始化加载状态
  loadingStates.set(viewId, false)

  tab.addEventListener('click', () => {
    setActiveTab(viewId)
    window.electronAPI.switchTab(viewId)
  })

  // 只有当标签数量大于1时才允许关闭
  const closeBtn = tab.querySelector('.close-btn')
  closeBtn.addEventListener('click', (e) => {
    e.stopPropagation()
    if (views.size > 1) {
      window.electronAPI.closeTab(viewId)
    } else {
      showToast('至少需要保留1个标签页')
    }
  })

  // 右键菜单
  tab.addEventListener('contextmenu', (e) => {
    e.preventDefault() // 阻止默认右键菜单
    // 可在此处传递元素信息（如ID）
    window.electronAPI.openContextMenu(viewId)
    // 保存事件目标（可选）
    window.selectedElement = e.target
  })

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

// 按 新页面 按钮
newTabBtn.addEventListener('click', () => {
  if (views.size < 10) {
    window.electronAPI.createNewTab()
  } else {
    showToast('最多只能创建10个标签页')
  }
})

// 按home按钮，创建home tab
homeBtn.addEventListener('click', () => {
  window.electronAPI.createHomeTab()
})

// 按settings按钮，创建设置 tab
settingsBtn.addEventListener('click', () => {
  window.electronAPI.createSettingsTab()
})

hashBtn.addEventListener('click', () => {
  window.electronAPI.createPythonTab()
})

// 响应 主页创建
window.electronAPI.onHomeCreated((event, viewId) => {
  views.add(viewId)
  const tab = createHomeElement(viewId)
  homeViewId = viewId
  // 将新标签插入到新建按钮之前
  const newTabBtn = document.getElementById('new-tab-btn')
  tabsContainer.insertBefore(tab, newTabBtn)

  setActiveTab(viewId)
  // 在浏览器模式下，需要调用 switchTab 来切换 iframe 显示
  window.electronAPI.switchTab(viewId)
  updateNewTabButtonVisibility() // 更新新建按钮显示状态
  setTimeout(updateScrollButtons, 0)
})

// 响应 设置页创建
window.electronAPI.onSettingsCreated((event, viewId) => {
  views.add(viewId)
  const tab = createSettingsElement(viewId)
  // 将新标签插入到新建按钮之前
  const newTabBtn = document.getElementById('new-tab-btn')
  tabsContainer.insertBefore(tab, newTabBtn)

  setActiveTab(viewId)
  // 在浏览器模式下，需要调用 switchTab 来切换 iframe 显示
  window.electronAPI.switchTab(viewId)
  updateNewTabButtonVisibility() // 更新新建按钮显示状态
  setTimeout(updateScrollButtons, 0)
})

window.electronAPI.onTabCreated((event, viewId) => {
  views.add(viewId)
  const tab = createTabElement(viewId)

  // 将新标签插入到新建按钮之前
  const newTabBtn = document.getElementById('new-tab-btn')
  tabsContainer.insertBefore(tab, newTabBtn)

  setActiveTab(viewId)
  // 在浏览器模式下，需要调用 switchTab 来切换 iframe 显示
  window.electronAPI.switchTab(viewId)
  updateNewTabButtonVisibility() // 更新新建按钮显示状态
  setTimeout(updateScrollButtons, 0)
})

window.electronAPI.onTabClosed((event, viewId) => {
  views.delete(viewId)
  loadingStates.delete(viewId) // 清理加载状态
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

// 初始化时请求创建第一个标签并设置新建按钮状态
window.electronAPI.createHomeTab()

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
  newTabBtn.style.display = views.size >= 10 ? 'none' : 'flex'
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
