/**
 * 侧边栏 ChatPanel Vue 挂载引导
 *
 * 在主窗口 index.html 中将 ChatPanel.vue 组件挂载到 #chat-panel-mount
 */
import { createApp } from 'vue'
import ChatPanel from './components/sidebar/ChatPanel.vue'

export function mountChatPanel() {
  const mountEl = document.getElementById('chat-panel-mount')
  if (!mountEl) {
    console.warn('[ChatPanel] #chat-panel-mount 未找到，跳过挂载')
    return
  }

  const app = createApp(ChatPanel)
  app.mount(mountEl)
  console.log('[ChatPanel] Vue 侧边栏已挂载')
}
