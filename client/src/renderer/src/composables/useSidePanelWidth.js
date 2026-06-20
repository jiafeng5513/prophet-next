import { onMounted, onUnmounted } from 'vue'

/**
 * 监听主进程侧栏宽度变化，同步更新 CSS 变量 --side-panel-width
 * 同时支持拖拽调整侧栏宽度
 * @param {import('vue').Ref<HTMLElement>} panelRef - side-panel 元素的 ref
 */
export function useSidePanelWidth(panelRef) {
  let cleanup = null

  onMounted(async () => {
    // 初始化时获取当前宽度
    if (window.electronAPI?.getSidePanelWidth) {
      const width = await window.electronAPI.getSidePanelWidth()
      if (width) {
        document.documentElement.style.setProperty('--side-panel-width', `${width}px`)
      }
    }

    // 监听后续变化
    if (window.electronAPI?.onSidePanelWidthChanged) {
      window.electronAPI.onSidePanelWidthChanged((width) => {
        document.documentElement.style.setProperty('--side-panel-width', `${width}px`)
      })
    }

    // 设置拖拽调整宽度
    if (panelRef?.value) {
      cleanup = setupResizeHandle(panelRef.value)
    }
  })

  onUnmounted(() => {
    if (cleanup) cleanup()
  })
}

/**
 * 为 side-panel 元素设置拖拽调整宽度
 */
function setupResizeHandle(panelEl) {
  const handle = panelEl.querySelector('.side-panel-resize-handle')
  if (!handle) return null

  const onMouseDown = (e) => {
    e.preventDefault()
    handle.classList.add('dragging')
    document.body.style.cursor = 'col-resize'
    document.body.style.userSelect = 'none'

    const panelLeft = panelEl.getBoundingClientRect().left

    const onMouseMove = (moveEvt) => {
      let newWidth = moveEvt.clientX - panelLeft
      newWidth = Math.max(150, Math.min(500, newWidth))
      document.documentElement.style.setProperty('--side-panel-width', `${newWidth}px`)
      if (window.electronAPI?.resizeExplorerPanel) {
        window.electronAPI.resizeExplorerPanel(newWidth)
      }
    }

    const onMouseUp = () => {
      handle.classList.remove('dragging')
      document.body.style.cursor = ''
      document.body.style.userSelect = ''
      document.removeEventListener('mousemove', onMouseMove)
      document.removeEventListener('mouseup', onMouseUp)
    }

    document.addEventListener('mousemove', onMouseMove)
    document.addEventListener('mouseup', onMouseUp)
  }

  handle.addEventListener('mousedown', onMouseDown)
  return () => handle.removeEventListener('mousedown', onMouseDown)
}

/**
 * Options API mixin：在 mounted 中调用以同步侧栏宽度并支持拖拽
 * @param {HTMLElement} panelEl - side-panel DOM 元素
 */
export function setupSidePanelWidth(panelEl) {
  if (window.electronAPI?.getSidePanelWidth) {
    window.electronAPI.getSidePanelWidth().then((w) => {
      if (w) document.documentElement.style.setProperty('--side-panel-width', `${w}px`)
    })
  }
  if (window.electronAPI?.onSidePanelWidthChanged) {
    window.electronAPI.onSidePanelWidthChanged((w) => {
      document.documentElement.style.setProperty('--side-panel-width', `${w}px`)
    })
  }
  if (panelEl) {
    setupResizeHandle(panelEl)
  }
}
