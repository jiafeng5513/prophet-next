// 设置页面脚本
document.addEventListener('DOMContentLoaded', async () => {
  // 这里可以添加设置页面的交互逻辑
  console.log('设置页面已加载')

  // 工作区目录
  const workspacePathInput = document.getElementById('workspace-path')
  const browseWorkspaceBtn = document.getElementById('browse-workspace-btn')

  // 加载工作区路径
  if (window.electronAPI && window.electronAPI.getWorkspacePath) {
    const wsPath = await window.electronAPI.getWorkspacePath()
    workspacePathInput.value = wsPath || ''
  }

  // 浏览按钮：打开目录选择对话框
  browseWorkspaceBtn.addEventListener('click', async () => {
    if (window.electronAPI && window.electronAPI.setWorkspacePath) {
      const newPath = await window.electronAPI.setWorkspacePath()
      if (newPath) {
        workspacePathInput.value = newPath
        console.log('[Settings] 工作区目录已更改为:', newPath)
      }
    }
  })

  // 示例：保存设置
  const themeSelect = document.getElementById('theme')
  const closeWarningCheckbox = document.getElementById('close-warning')
  const maxTabsInput = document.getElementById('max-tabs')
  const dataSourceSelect = document.getElementById('data-source')
  
  // 加载保存的设置
  const savedTheme = localStorage.getItem('theme') || 'dark'
  const savedCloseWarning = localStorage.getItem('close-warning') === 'true'
  const savedMaxTabs = localStorage.getItem('max-tabs') || '10'
  
  // 从主进程获取数据源设置（解决跨 partition 隔离问题）
  let savedDataSource = 'binance'
  if (window.electronAPI && window.electronAPI.getDataSource) {
    savedDataSource = await window.electronAPI.getDataSource()
  } else {
    savedDataSource = localStorage.getItem('data-source') || 'binance'
  }
  
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
      
      // 通过 IPC 通知主进程更新数据源（解决跨 partition 隔离问题）
      if (window.electronAPI && window.electronAPI.setDataSource) {
        window.electronAPI.setDataSource(newDataSource)
      }
      
      // 通知主进程关闭所有图表页面
      if (window.electronAPI && window.electronAPI.closeAllChartTabs) {
        console.log('[Settings] 调用 closeAllChartTabs API')
        window.electronAPI.closeAllChartTabs()
      }
    } else {
      // 用户取消，恢复原来的值
      dataSourceSelect.value = currentDataSource
      console.log('[Settings] 用户取消切换，恢复原数据源:', currentDataSource)
    }
  })

  // =====================
  // DSA 配置管理
  // =====================
  const dsaPathInput = document.getElementById('dsa-path')
  const browseDsaBtn = document.getElementById('browse-dsa-btn')
  const pythonPathInput = document.getElementById('python-path')
  const browsePythonBtn = document.getElementById('browse-python-btn')
  const dsaPortInput = document.getElementById('dsa-port')
  const llmProviderSelect = document.getElementById('llm-provider')
  const llmApiKeyInput = document.getElementById('llm-api-key')
  const toggleApiKeyBtn = document.getElementById('toggle-api-key-btn')
  const llmModelInput = document.getElementById('llm-model')
  const searchApiKeyInput = document.getElementById('search-api-key')
  const dsaStatusDot = document.getElementById('dsa-status-dot')
  const dsaStatusText = document.getElementById('dsa-status-text')
  const dsaStartBtn = document.getElementById('dsa-start-btn')
  const dsaStopBtn = document.getElementById('dsa-stop-btn')
  const dsaStatusDesc = document.getElementById('dsa-status-desc')

  // 加载 DSA 配置
  if (window.electronAPI && window.electronAPI.getDsaConfig) {
    const dsaConfig = await window.electronAPI.getDsaConfig()
    dsaPathInput.value = dsaConfig.dsaPath || ''
    pythonPathInput.value = dsaConfig.pythonPath || ''
    dsaPortInput.value = dsaConfig.port || 8000
    llmProviderSelect.value = dsaConfig.llmProvider || ''
    llmApiKeyInput.value = dsaConfig.llmApiKey || ''
    llmModelInput.value = dsaConfig.llmModel || ''
    searchApiKeyInput.value = dsaConfig.searchApiKey || ''
  }

  // 加载 DSA 服务状态
  if (window.electronAPI && window.electronAPI.getDsaStatus) {
    const statusInfo = await window.electronAPI.getDsaStatus()
    updateDsaStatusUI(statusInfo.status)
  }

  // 监听 DSA 服务状态变化
  if (window.electronAPI && window.electronAPI.onDsaStatusChanged) {
    window.electronAPI.onDsaStatusChanged((data) => {
      updateDsaStatusUI(data.status)
    })
  }

  function updateDsaStatusUI(status) {
    const statusMap = {
      stopped: { color: '#666', text: '未启动', showStart: true, showStop: false },
      starting: { color: '#d29922', text: '正在启动...', showStart: false, showStop: false },
      running: { color: '#2ea043', text: '运行中', showStart: false, showStop: true },
      error: { color: '#da3633', text: '启动失败', showStart: true, showStop: false }
    }
    const info = statusMap[status] || statusMap.stopped
    dsaStatusDot.style.background = info.color
    dsaStatusText.textContent = info.text
    dsaStartBtn.style.display = info.showStart ? '' : 'none'
    dsaStopBtn.style.display = info.showStop ? '' : 'none'
  }

  // 保存 DSA 配置的通用函数
  async function saveDsaConfig() {
    if (!window.electronAPI || !window.electronAPI.setDsaConfig) return
    await window.electronAPI.setDsaConfig({
      dsaPath: dsaPathInput.value,
      pythonPath: pythonPathInput.value,
      port: parseInt(dsaPortInput.value) || 8000,
      llmProvider: llmProviderSelect.value,
      llmApiKey: llmApiKeyInput.value,
      llmModel: llmModelInput.value,
      searchApiKey: searchApiKeyInput.value
    })
    console.log('[Settings] DSA 配置已保存')
  }

  // 浏览 DSA 路径
  browseDsaBtn.addEventListener('click', async () => {
    if (window.electronAPI && window.electronAPI.browseDsaPath) {
      const newPath = await window.electronAPI.browseDsaPath()
      if (newPath) {
        dsaPathInput.value = newPath
        await saveDsaConfig()
      }
    }
  })

  // 浏览 Python 路径
  browsePythonBtn.addEventListener('click', async () => {
    if (window.electronAPI && window.electronAPI.browsePythonPath) {
      const newPath = await window.electronAPI.browsePythonPath()
      if (newPath) {
        pythonPathInput.value = newPath
        await saveDsaConfig()
      }
    }
  })

  // 各配置项变化时自动保存
  dsaPortInput.addEventListener('change', saveDsaConfig)
  llmProviderSelect.addEventListener('change', saveDsaConfig)
  llmApiKeyInput.addEventListener('change', saveDsaConfig)
  llmModelInput.addEventListener('change', saveDsaConfig)
  searchApiKeyInput.addEventListener('change', saveDsaConfig)

  // API Key 显示/隐藏切换
  toggleApiKeyBtn.addEventListener('click', () => {
    if (llmApiKeyInput.type === 'password') {
      llmApiKeyInput.type = 'text'
      toggleApiKeyBtn.textContent = '隐藏'
    } else {
      llmApiKeyInput.type = 'password'
      toggleApiKeyBtn.textContent = '显示'
    }
  })

  // 启动 DSA 服务
  dsaStartBtn.addEventListener('click', async () => {
    if (!dsaPathInput.value) {
      await showConfirmDialog('提示', '请先设置 DSA 项目路径', '确定', '确定')
      return
    }
    if (!llmProviderSelect.value || !llmApiKeyInput.value) {
      const proceed = await showConfirmDialog(
        '提示',
        '尚未配置 LLM API Key，部分功能可能无法正常工作。是否继续启动？',
        '继续',
        '取消'
      )
      if (!proceed) return
    }

    await saveDsaConfig()
    dsaStartBtn.style.display = 'none'
    updateDsaStatusUI('starting')

    if (window.electronAPI && window.electronAPI.startDsaServer) {
      const result = await window.electronAPI.startDsaServer()
      if (result.success) {
        updateDsaStatusUI('running')
        dsaStatusDesc.textContent = `服务运行在 http://127.0.0.1:${dsaPortInput.value}`
      } else {
        updateDsaStatusUI('error')
        dsaStatusDesc.textContent = `启动失败: ${result.error}`
      }
    }
  })

  // 停止 DSA 服务
  dsaStopBtn.addEventListener('click', async () => {
    if (window.electronAPI && window.electronAPI.stopDsaServer) {
      await window.electronAPI.stopDsaServer()
      updateDsaStatusUI('stopped')
      dsaStatusDesc.textContent = '启动 DSA 后端服务后，可使用股票分析和问股功能'
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
