<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { IconAlertTriangle, IconCheck, IconLoader } from '@tabler/icons-vue'
import { syncVideoTask } from '../api/mockApi.js'
import { navigate, state, updateCurrentTask } from '../state/creationState.js'

const task = state.currentTask
const polling = ref(false)
const error = ref('')
let pollTimer = null

const steps = [
  { label: '任务已提交', key: 'submitted' },
  { label: '数字人生成中', key: 'generating' },
  { label: '成片已完成', key: 'completed' },
]

const currentStepIndex = computed(() => {
  if (task?.status === 'completed') return 2
  if (task?.status === 'generating') return 1
  return 0
})

function schedulePoll() {
  if (state.currentPage !== 'generating') return
  pollTimer = window.setTimeout(refreshStatus, 3000)
}

async function refreshStatus() {
  if (!task?.id || polling.value) return
  polling.value = true
  try {
    const result = await syncVideoTask(task.id)
    updateCurrentTask(result.task)
    if (result.task.status === 'completed') {
      navigate('video-preview')
      return
    }
    if (result.task.status === 'failed') {
      error.value = result.task.error_message || '成片生成失败，积分会按规则退回'
      return
    }
    schedulePoll()
  } catch (reason) {
    error.value = reason.message || '查询生成状态失败，稍后将自动重试'
    schedulePoll()
  } finally {
    polling.value = false
  }
}

onMounted(refreshStatus)

onUnmounted(() => {
  if (pollTimer) window.clearTimeout(pollTimer)
})
</script>

<template>
  <div>
    <h1 class="page-title">{{ task?.title || '生成中' }}</h1>

    <div class="card-strong generation-status">
      <div class="progress-ring" :class="{ failed: !!error }">
        <IconAlertTriangle v-if="error" :size="56" stroke-width="1.7" />
        <IconCheck v-else-if="task?.status === 'completed'" :size="56" stroke-width="2" />
        <IconLoader v-else :size="56" stroke-width="1.5" />
      </div>
      <p>{{ error || '数字人正在生成，通常需要几分钟。离开页面后也会继续处理。' }}</p>
    </div>

    <div class="card mt-20">
      <div
        v-for="(step, index) in steps"
        :key="step.key"
        class="step-row"
        :class="{
          done: index < currentStepIndex,
          current: index === currentStepIndex,
          pending: index > currentStepIndex,
        }"
      >
        <span class="step-status">
          <IconCheck v-if="index < currentStepIndex" :size="16" stroke-width="2.5" />
          <IconLoader v-else-if="index === currentStepIndex && !error" :size="16" stroke-width="2" />
          <IconAlertTriangle v-else-if="index === currentStepIndex" :size="16" stroke-width="2" />
          <span v-else class="step-num">{{ index + 1 }}</span>
        </span>
        <span class="step-text">{{ step.label }}</span>
      </div>
    </div>

    <div class="generation-actions mt-24">
      <button v-if="error" class="action-btn secondary" type="button" @click="navigate('video-upload')">
        返回重试
      </button>
      <button class="action-btn secondary" type="button" @click="navigate('task-list')">
        查看任务记录
      </button>
    </div>
  </div>
</template>

<style scoped>
.generation-status {
  padding: 32px 18px;
  text-align: center;
}

.generation-status p {
  margin: 16px 0 0;
  font-size: 15px;
  line-height: 1.6;
  font-weight: 600;
}

.progress-ring {
  display: grid;
  place-items: center;
  color: var(--accent-2);
}

.progress-ring:not(.failed) svg {
  animation: spin 1.5s linear infinite;
}

.progress-ring.failed {
  color: var(--danger);
}

.step-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 0;
  border-bottom: 1px solid var(--line);
}

.step-row:last-child {
  border-bottom: none;
}

.step-status {
  width: 28px;
  height: 28px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  flex-shrink: 0;
}

.step-row.done .step-status {
  color: #0a0e14;
  background: var(--accent);
}

.step-row.current .step-status {
  color: #0a0e14;
  background: var(--accent-2);
}

.step-row.pending .step-status {
  color: var(--muted);
  background: var(--card);
}

.step-row.current .step-text {
  color: var(--accent-2);
  font-weight: 700;
}

.step-row.pending .step-text {
  color: var(--muted);
}

.step-num {
  font-size: 12px;
  font-weight: 700;
}

.generation-actions {
  display: grid;
  gap: 10px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
