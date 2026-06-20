/**
 * Annotation Service — K 线图信号标注管理
 *
 * 职责:
 * 1. 标注的 CRUD (创建/读取/删除)
 * 2. localStorage 持久化
 * 3. 从 Agent 分析结果创建标注
 * 4. IPC 通知 Chart 标签页渲染标注
 */

import type {
  ChartAnnotation,
  CreateAnnotationParams,
  AnnotationType
} from '../types/annotation'
import type { DashboardData } from './chatService'

const STORAGE_KEY = 'prophet-annotations'

/** 生成唯一 ID */
function generateId(): string {
  return `ann_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`
}

/**
 * 从 localStorage 加载所有标注
 */
function loadAll(): ChartAnnotation[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? JSON.parse(raw) : []
  } catch {
    return []
  }
}

/**
 * 保存所有标注到 localStorage
 */
function saveAll(annotations: ChartAnnotation[]): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(annotations))
}

/**
 * 获取指定标的的标注列表
 */
export function loadForSymbol(symbol: string): ChartAnnotation[] {
  return loadAll().filter(a => a.symbol === symbol)
}

/**
 * 创建标注并持久化
 */
export function createAnnotation(params: CreateAnnotationParams): ChartAnnotation {
  const annotation: ChartAnnotation = { id: generateId(), ...params }
  const all = loadAll()
  all.push(annotation)
  saveAll(all)
  return annotation
}

/**
 * 删除标注
 */
export function removeAnnotation(id: string): void {
  const all = loadAll().filter(a => a.id !== id)
  saveAll(all)
}

/**
 * 清除指定标的的所有标注
 */
export function clearAnnotationsForSymbol(symbol: string): void {
  const all = loadAll().filter(a => a.symbol !== symbol)
  saveAll(all)
}

/**
 * 从 Agent Dashboard 结果创建标注
 */
export function createFromDashboard(
  symbol: string,
  dashboard: DashboardData,
  sessionId?: string
): ChartAnnotation | null {
  if (!dashboard.signal) return null

  const type: AnnotationType =
    dashboard.signal === 'buy' ? 'buy'
      : dashboard.signal === 'sell' ? 'sell'
        : dashboard.signal === 'hold' ? 'hold'
          : 'alert'

  const confidence = dashboard.confidence ?? 0
  const label = `${dashboard.signal} (${(confidence * 100).toFixed(0)}%)`

  return createAnnotation({
    symbol,
    timestamp: Date.now(),
    type,
    source: 'agent',
    label,
    price: 0, // 由 Chart 侧获取当前价格填充
    metadata: {
      agent_mode: (dashboard as Record<string, unknown>).mode as string | undefined,
      confidence,
      signal: dashboard.signal,
      session_id: sessionId
    }
  })
}

/**
 * 通过 IPC 将标注发送到 Chart 标签页渲染
 */
export function pushAnnotationsToChart(symbol: string, annotations: ChartAnnotation[]): void {
  if (window.electronAPI?.invoke) {
    window.electronAPI.invoke('chart:add-annotations', { symbol, annotations })
  }
}

/**
 * 便捷方法: 从 Dashboard 创建标注并推送到 Chart
 */
export function annotateFromDashboard(
  symbol: string,
  dashboard: DashboardData,
  sessionId?: string
): ChartAnnotation | null {
  const annotation = createFromDashboard(symbol, dashboard, sessionId)
  if (annotation) {
    pushAnnotationsToChart(symbol, [annotation])
  }
  return annotation
}
