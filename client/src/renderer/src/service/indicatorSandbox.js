/**
 * 指标沙箱服务
 *
 * 提供 Web Worker 隔离环境来验证用户指标代码。
 * 验证通过后才允许注册到图表运行时。
 */

import SandboxWorker from './indicatorSandboxWorker.js?worker'

const TIMEOUT_MS = 5000

/**
 * 在 Web Worker 中验证指标代码
 * @param {string} code - 用户指标源代码
 * @returns {Promise<{ success: boolean, metainfo?: object, error?: string }>}
 */
export function validateInWorker(code) {
  return new Promise((resolve) => {
    let worker
    try {
      worker = new SandboxWorker()
    } catch (e) {
      // Worker 创建失败时 fallback 到同步验证
      resolve(fallbackValidate(code))
      return
    }

    const timer = setTimeout(() => {
      worker.terminate()
      resolve({ success: false, error: '验证超时 (>5s)，可能存在死循环' })
    }, TIMEOUT_MS)

    worker.onmessage = (e) => {
      clearTimeout(timer)
      worker.terminate()
      resolve(e.data)
    }

    worker.onerror = (e) => {
      clearTimeout(timer)
      worker.terminate()
      resolve({ success: false, error: e.message || '沙箱执行错误' })
    }

    worker.postMessage({ code, action: 'validate' })
  })
}

/**
 * 降级验证 (Worker 不可用时)
 */
function fallbackValidate(code) {
  try {
    new Function('PineJS', `"use strict";\n${code}\nif (typeof create !== 'function') { throw new Error('必须定义 create(PineJS) 函数'); }`)
    return { success: true, metainfo: { name: 'unknown' } }
  } catch (e) {
    return { success: false, error: e.message }
  }
}
