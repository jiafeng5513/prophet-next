// 设置页面脚本
document.addEventListener('DOMContentLoaded', () => {
  // 这里可以添加设置页面的交互逻辑
  console.log('设置页面已加载')
  
  // 示例：保存设置
  const themeSelect = document.getElementById('theme')
  const closeWarningCheckbox = document.getElementById('close-warning')
  const maxTabsInput = document.getElementById('max-tabs')
  
  // 加载保存的设置
  // TODO: 从本地存储或配置文件中加载设置
  
  // 监听设置变化
  themeSelect.addEventListener('change', (e) => {
    console.log('主题已更改:', e.target.value)
    // TODO: 保存设置
  })
  
  closeWarningCheckbox.addEventListener('change', (e) => {
    console.log('关闭警告已更改:', e.target.checked)
    // TODO: 保存设置
  })
  
  maxTabsInput.addEventListener('change', (e) => {
    console.log('最大标签页数已更改:', e.target.value)
    // TODO: 保存设置
  })
})
