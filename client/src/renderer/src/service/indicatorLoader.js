/**
 * 自定义指标加载器
 *
 * 从主进程获取自定义指标代码，在安全沙箱中实例化后供 TradingView 使用。
 * 安全机制: 静态正则检查 + Function 构造器遮蔽全局变量
 * 验证机制: Web Worker 沙箱异步验证 (indicatorSandbox.js)
 * 热加载: 监听 indicator:code-updated → 重新实例化指标 → 刷新图表
 */

import { validateInWorker } from './indicatorSandbox'

// 已加载指标的缓存: id → { code, indicator, disabled }
const loadedIndicators = new Map()

// 崩溃计数器: id → count (连续失败次数)
const crashCounter = new Map()
const MAX_CRASHES = 3

// 危险模式静态检查
const BLOCKED_PATTERNS = [
  /\brequire\s*\(/,
  /\bprocess\b/,
  /\b__dirname\b/,
  /\b__filename\b/,
  /\bglobal\b/,
  /\bwindow\b/,
  /\bdocument\b/,
  /\bfetch\s*\(/,
  /\bXMLHttpRequest\b/,
  /\bWebSocket\b/,
  /\beval\s*\(/,
  /\bFunction\s*\(/,
  /\bimportScripts\b/,
  /\belectron\b/i
]

/**
 * 静态安全检查
 * @param {string} code
 * @returns {{ safe: boolean, violation?: string }}
 */
function staticSecurityCheck(code) {
  for (const pattern of BLOCKED_PATTERNS) {
    if (pattern.test(code)) {
      return { safe: false, violation: `检测到禁止的代码模式: ${pattern.source}` }
    }
  }
  return { safe: true }
}

/**
 * 在沙箱中实例化指标代码 (同步，用于图表渲染时)
 * 使用 Function 构造函数创建隔离作用域，禁止访问全局对象
 *
 * @param {string} code - 指标源代码
 * @param {object} PineJS - TradingView PineJS 对象
 * @returns {object|null} CustomIndicator 或 null
 */
function sandboxEvaluate(code, PineJS) {
  const check = staticSecurityCheck(code)
  if (!check.safe) {
    console.error(`[IndicatorLoader] 安全检查失败: ${check.violation}`)
    return null
  }

  try {
    const factory = new Function(
      'PineJS',
      'window', 'document', 'globalThis', 'global',
      'require', 'process', 'fetch', 'XMLHttpRequest', 'WebSocket',
      'eval', 'Function',
      `"use strict";
      ${code}
      if (typeof create !== 'function') {
        throw new Error('指标代码必须定义 create(PineJS) 函数');
      }
      return create(PineJS);`
    )

    const indicator = factory(
      PineJS,
      undefined, undefined, undefined, undefined,
      undefined, undefined, undefined, undefined, undefined,
      undefined, undefined
    )

    if (!indicator || !indicator.name || !indicator.metainfo || !indicator.constructor) {
      console.error('[IndicatorLoader] 指标结构不完整, 需要 name/metainfo/constructor')
      return null
    }

    return indicator
  } catch (e) {
    console.error(`[IndicatorLoader] 沙箱执行失败:`, e.message)
    return null
  }
}

/**
 * 加载所有自定义指标 (供 custom_indicators_getter 调用)
 * @param {object} PineJS
 * @returns {Promise<object[]>}
 */
export async function loadCustomIndicators(PineJS) {
  const indicators = []

  try {
    let activeIndicators = []
    if (window.electronAPI && window.electronAPI.getActiveIndicators) {
      activeIndicators = await window.electronAPI.getActiveIndicators()
    }

    for (const ind of activeIndicators) {
      // 跳过已被自动禁用的指标
      const cached = loadedIndicators.get(ind.id)
      if (cached && cached.disabled) {
        console.warn(`[IndicatorLoader] 指标 ${ind.id} 已被禁用 (连续崩溃), 跳过`)
        continue
      }

      const result = sandboxEvaluate(ind.code, PineJS)
      if (result) {
        loadedIndicators.set(ind.id, { code: ind.code, indicator: result, disabled: false })
        crashCounter.set(ind.id, 0) // 加载成功，重置崩溃计数
        indicators.push(result)
      }
    }
  } catch (e) {
    console.error('[IndicatorLoader] 加载自定义指标失败:', e)
  }

  return indicators
}

/**
 * 热加载单个指标 (代码更新后调用)
 * 先用 Worker 验证，通过后更新缓存
 *
 * @param {string} id - 指标 ID
 * @param {string} code - 新代码
 * @returns {Promise<{ success: boolean, error?: string }>}
 */
export async function hotReloadIndicator(id, code) {
  // 1. 静态安全检查
  const check = staticSecurityCheck(code)
  if (!check.safe) {
    return { success: false, error: check.violation }
  }

  // 2. Worker 沙箱验证
  const validation = await validateInWorker(code)
  if (!validation.success) {
    return { success: false, error: validation.error }
  }

  // 3. 验证通过，更新缓存 (indicator 置空，下次 getter 调用时重建)
  loadedIndicators.set(id, { code, indicator: null, disabled: false })
  crashCounter.set(id, 0)

  return { success: true }
}

/**
 * 标记指标执行崩溃
 * 连续崩溃超过阈值则自动禁用
 *
 * @param {string} id
 * @returns {boolean} true = 已自动禁用
 */
export function reportCrash(id) {
  const count = (crashCounter.get(id) || 0) + 1
  crashCounter.set(id, count)

  if (count >= MAX_CRASHES) {
    const cached = loadedIndicators.get(id)
    if (cached) {
      cached.disabled = true
    }
    console.error(`[IndicatorLoader] 指标 ${id} 连续崩溃 ${count} 次，已自动禁用`)
    return true
  }
  return false
}

/**
 * 手动启用/禁用指标
 */
export function setIndicatorEnabled(id, enabled) {
  const cached = loadedIndicators.get(id)
  if (cached) {
    cached.disabled = !enabled
    if (enabled) crashCounter.set(id, 0)
  }
}

/**
 * 获取所有已加载指标的状态
 */
export function getIndicatorStatus() {
  const status = []
  for (const [id, data] of loadedIndicators) {
    status.push({ id, disabled: data.disabled, hasIndicator: !!data.indicator })
  }
  return status
}

/**
 * 注册热加载监听器
 * 在图表组件 mounted 后调用
 * @param {Function} onReload - 回调函数 (id, action) → 触发图表刷新
 *   action: 'update' | 'remove'
 */
export function setupHotReload(onReload) {
  if (!window.electronAPI) return

  if (window.electronAPI.onIndicatorCodeUpdated) {
    window.electronAPI.onIndicatorCodeUpdated(async ({ id, code }) => {
      console.log(`[IndicatorLoader] 收到热加载通知: ${id}`)

      const result = await hotReloadIndicator(id, code)

      if (result.success) {
        console.log(`[IndicatorLoader] 指标 ${id} 验证通过，通知图表刷新`)
        if (onReload) onReload(id, 'update')
      } else {
        console.error(`[IndicatorLoader] 指标 ${id} 验证失败: ${result.error}`)
        // 通知编辑器验证失败（通过 IPC 回传）
      }
    })
  }

  if (window.electronAPI.onIndicatorRemoved) {
    window.electronAPI.onIndicatorRemoved(({ id }) => {
      console.log(`[IndicatorLoader] 指标已移除: ${id}`)
      loadedIndicators.delete(id)
      crashCounter.delete(id)
      if (onReload) onReload(id, 'remove')
    })
  }
}
