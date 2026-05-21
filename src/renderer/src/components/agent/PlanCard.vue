<template>
  <div class="plan-card">
    <div class="plan-card__header">
      <span class="plan-icon">📋</span>
      <span class="plan-title">分析计划</span>
      <span v-if="plan.estimated_time" class="plan-estimate">预估 {{ plan.estimated_time }}</span>
    </div>

    <div class="plan-card__steps">
      <div
        v-for="(step, idx) in plan.steps"
        :key="idx"
        class="plan-step"
        :class="{ 'plan-step--done': step.done, 'plan-step--running': step.running }"
      >
        <span class="plan-step__number">{{ idx + 1 }}</span>
        <span class="plan-step__text">{{ step.description }}</span>
        <span v-if="step.done" class="plan-step__check">✅</span>
        <span v-else-if="step.running" class="plan-step__spinner">⏳</span>
      </div>
    </div>

    <div v-if="plan.estimated_tokens" class="plan-card__meta">
      预估 Token: ~{{ plan.estimated_tokens }}
    </div>

    <div v-if="!executing" class="plan-card__actions">
      <button class="plan-btn plan-btn--primary" @click="$emit('execute')">▶ 执行计划</button>
      <button class="plan-btn plan-btn--secondary" @click="$emit('modify')">✏️ 修改</button>
      <button class="plan-btn plan-btn--ghost" @click="$emit('cancel')">取消</button>
    </div>
  </div>
</template>

<script setup lang="ts">
export interface PlanStep {
  description: string
  done?: boolean
  running?: boolean
}

export interface AnalysisPlan {
  steps: PlanStep[]
  estimated_time?: string
  estimated_tokens?: number
}

defineProps<{
  plan: AnalysisPlan
  executing?: boolean
}>()

defineEmits<{
  execute: []
  modify: []
  cancel: []
}>()
</script>

<style scoped>
.plan-card {
  background: #1a2634;
  border: 1px solid #2d4a5e;
  border-radius: 10px;
  padding: 16px;
  margin-top: 12px;
}

.plan-card__header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}

.plan-icon {
  font-size: 18px;
}

.plan-title {
  font-size: 14px;
  font-weight: 600;
  color: #ffffff;
}

.plan-estimate {
  margin-left: auto;
  font-size: 12px;
  color: #8b9bb4;
}

.plan-card__steps {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 12px;
}

.plan-step {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  background: #0d1b2a;
  border-radius: 6px;
  font-size: 13px;
  color: #c0c8d4;
  transition: background 0.2s;
}

.plan-step--done {
  opacity: 0.7;
}

.plan-step--running {
  background: #1b2d3e;
  border-left: 3px solid #3b82f6;
}

.plan-step__number {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #2d4a5e;
  color: #8b9bb4;
  font-size: 11px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.plan-step--done .plan-step__number {
  background: #166534;
  color: #4ade80;
}

.plan-step--running .plan-step__number {
  background: #1e3a5f;
  color: #60a5fa;
}

.plan-step__text {
  flex: 1;
}

.plan-step__check,
.plan-step__spinner {
  font-size: 14px;
}

.plan-card__meta {
  font-size: 12px;
  color: #6b7b8e;
  margin-bottom: 12px;
}

.plan-card__actions {
  display: flex;
  gap: 8px;
}

.plan-btn {
  padding: 6px 14px;
  border-radius: 6px;
  font-size: 13px;
  cursor: pointer;
  border: none;
  transition: background 0.2s;
}

.plan-btn--primary {
  background: #3b82f6;
  color: #ffffff;
}

.plan-btn--primary:hover {
  background: #2563eb;
}

.plan-btn--secondary {
  background: #374151;
  color: #d1d5db;
}

.plan-btn--secondary:hover {
  background: #4b5563;
}

.plan-btn--ghost {
  background: transparent;
  color: #8b9bb4;
}

.plan-btn--ghost:hover {
  background: #1f2937;
}
</style>
