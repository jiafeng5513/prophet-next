/**
 * K 线图信号标注 — 类型定义
 */

/** 标注信号类型 */
export type AnnotationType = 'buy' | 'sell' | 'hold' | 'alert'

/** 标注来源 */
export type AnnotationSource = 'agent' | 'user' | 'backtest'

/** 单条标注 */
export interface ChartAnnotation {
  id: string
  symbol: string
  /** Unix 毫秒时间戳 */
  timestamp: number
  type: AnnotationType
  source: AnnotationSource
  label: string
  price: number
  metadata?: {
    agent_mode?: string
    confidence?: number
    signal?: string
    session_id?: string
  }
}

/** 标注图层 */
export interface AnnotationLayer {
  annotations: ChartAnnotation[]
  visible: boolean
  color: string
}

/** 标注创建参数（不含 id） */
export type CreateAnnotationParams = Omit<ChartAnnotation, 'id'>
