// 设置页面脚本
document.addEventListener('DOMContentLoaded', () => {
  // 这里可以添加设置页面的交互逻辑
  console.log('设置页面已加载')
  
  // 示例：保存设置
  const themeSelect = document.getElementById('theme')
  const closeWarningCheckbox = document.getElementById('close-warning')
  const maxTabsInput = document.getElementById('max-tabs')
  const dataSourceSelect = document.getElementById('data-source')
  
  // 加载保存的设置
  const savedTheme = localStorage.getItem('theme') || 'dark'
  const savedCloseWarning = localStorage.getItem('close-warning') === 'true'
  const savedMaxTabs = localStorage.getItem('max-tabs') || '10'
  const savedDataSource = localStorage.getItem('data-source') || 'binance'
  
  // 恢复设置值
  themeSelect.value = savedTheme
  closeWarningCheckbox.checked = savedCloseWarning
  maxTabsInput.value = savedMaxTabs
  dataSourceSelect.value = savedDataSource
  
  // 监听设置变化
  themeSelect.addEventListener('change', (e) => {
    console.log('主题已更改:', e.target.value)
    localStorage.setItem('theme', e.target.value)
  })
  
  closeWarningCheckbox.addEventListener('change', (e) => {
    console.log('关闭警告已更改:', e.target.checked)
    localStorage.setItem('close-warning', e.target.checked.toString())
  })
  
  maxTabsInput.addEventListener('change', (e) => {
    console.log('最大标签页数已更改:', e.target.value)
    localStorage.setItem('max-tabs', e.target.value)
  })
  
  // 数据源切换处理
  dataSourceSelect.addEventListener('change', async (e) => {
    const newDataSource = e.target.value
    const currentDataSource = localStorage.getItem('data-source') || 'binance'
    
    // 如果数据源没有变化，直接返回
    if (newDataSource === currentDataSource) {
      return
    }
    
    // 弹出确认对话框
    const confirmed = await showConfirmDialog(
      '切换数据源',
      '切换数据源后，所有已打开的图表页面都会关闭。确定要继续吗？',
      '确定',
      '取消'
    )
    
    if (confirmed) {
      // 保存新的数据源设置
      localStorage.setItem('data-source', newDataSource)
      console.log('[Settings] 数据源已切换为:', newDataSource)
      
      // 触发自定义事件，通知同窗口内的其他页面数据源已变化
      window.dispatchEvent(new CustomEvent('dataSourceChanged', { 
        detail: { dataSource: newDataSource } 
      }))
      console.log('[Settings] 已触发 dataSourceChanged 事件')
      
      // 通知主进程关闭所有图表页面
      if (window.electronAPI && window.electronAPI.closeAllChartTabs) {
        console.log('[Settings] 调用 closeAllChartTabs API')
        window.electronAPI.closeAllChartTabs()
      } else {
        // 浏览器模式下的处理
        console.log('[Settings] 浏览器模式：需要关闭所有图表页面')
        if (window.electronAPI && window.electronAPI.closeAllChartTabs) {
          window.electronAPI.closeAllChartTabs()
        }
      }
    } else {
      // 用户取消，恢复原来的值
      dataSourceSelect.value = currentDataSource
      console.log('[Settings] 用户取消切换，恢复原数据源:', currentDataSource)
    }
  })
})

// 显示确认对话框
function showConfirmDialog(title, message, confirmText, cancelText) {
  return new Promise((resolve) => {
    // 创建对话框遮罩层
    const overlay = document.createElement('div')
    overlay.style.cssText = `
      position: fixed;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      background: rgba(0, 0, 0, 0.5);
      display: flex;
      justify-content: center;
      align-items: center;
      z-index: 10000;
    `
    
    // 创建对话框
    const dialog = document.createElement('div')
    dialog.style.cssText = `
      background: #2e2c29;
      border: 1px solid #444;
      border-radius: 8px;
      padding: 24px;
      max-width: 400px;
      width: 90%;
      box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
    `
    
    dialog.innerHTML = `
      <h3 style="margin: 0 0 16px 0; font-size: 18px; color: #ffffff;">${title}</h3>
      <p style="margin: 0 0 24px 0; font-size: 14px; color: #cccccc; line-height: 1.5;">${message}</p>
      <div style="display: flex; gap: 12px; justify-content: flex-end;">
        <button id="cancel-btn" style="
          padding: 8px 16px;
          background: #1a1a1a;
          border: 1px solid #444;
          border-radius: 4px;
          color: #ffffff;
          cursor: pointer;
          font-size: 14px;
        ">${cancelText}</button>
        <button id="confirm-btn" style="
          padding: 8px 16px;
          background: #4a9eff;
          border: 1px solid #4a9eff;
          border-radius: 4px;
          color: #ffffff;
          cursor: pointer;
          font-size: 14px;
        ">${confirmText}</button>
      </div>
    `
    
    overlay.appendChild(dialog)
    document.body.appendChild(overlay)
    
    // 确认按钮
    const confirmBtn = dialog.querySelector('#confirm-btn')
    confirmBtn.addEventListener('click', () => {
      document.body.removeChild(overlay)
      resolve(true)
    })
    
    // 取消按钮
    const cancelBtn = dialog.querySelector('#cancel-btn')
    cancelBtn.addEventListener('click', () => {
      document.body.removeChild(overlay)
      resolve(false)
    })
    
    // 点击遮罩层关闭
    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) {
        document.body.removeChild(overlay)
        resolve(false)
      }
    })
    
    // 按钮悬停效果
    confirmBtn.addEventListener('mouseenter', () => {
      confirmBtn.style.background = '#5aaeff'
    })
    confirmBtn.addEventListener('mouseleave', () => {
      confirmBtn.style.background = '#4a9eff'
    })
    
    cancelBtn.addEventListener('mouseenter', () => {
      cancelBtn.style.background = '#2a2a2a'
    })
    cancelBtn.addEventListener('mouseleave', () => {
      cancelBtn.style.background = '#1a1a1a'
    })
  })
}
