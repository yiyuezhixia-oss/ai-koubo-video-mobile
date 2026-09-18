<script setup>
import { computed } from 'vue'
import {
  IconVideo,
  IconAlertTriangle,
  IconLoader,
} from '@tabler/icons-vue'
import { navigate, setCurrentTask } from '../state/creationState.js'

const props = defineProps({
  task: {
    type: Object,
    required: true,
  },
})

const statusMap = {
  draft: { label: '草稿', class: 'status-tag-warning' },
  rewriting: { label: '改写中', class: 'status-tag-warning' },
  rewrite_done: { label: '待生成配音', class: 'status-tag-warning' },
  voice_selecting: { label: '选音色', class: 'status-tag-warning' },
  tts_generating: { label: '配音中', class: 'status-tag-warning' },
  tts_done: { label: '待上传视频', class: 'status-tag-warning' },
  video_uploading: { label: '待上传', class: 'status-tag-warning' },
  video_uploaded: { label: '视频已上传', class: 'status-tag-warning' },
  video_generating: { label: '生成中', class: 'status-tag-warning' },
  generating: { label: '生成中', class: 'status-tag-warning' },
  completed: { label: '已完成', class: 'status-tag-success' },
  failed: { label: '失败', class: 'status-tag-failed' },
}

const statusInfo = computed(() => statusMap[props.task.status] || { label: props.task.status, class: 'status-tag-warning' })
const displayTime = computed(() => {
  if (!props.task.updated_at) return '时间未知'
  return new Intl.DateTimeFormat('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  }).format(new Date(props.task.updated_at))
})
const mediaDuration = computed(() =>
  props.task.output_video_file?.duration
  || props.task.tts_audio_file?.duration
  || props.task.source_video_file?.duration
  || 0,
)
const displayDuration = computed(() => {
  const seconds = Math.round(mediaDuration.value)
  if (!seconds) return ''
  return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, '0')}`
})

const statusPageMap = {
  draft: 'script-input',
  rewriting: 'rewrite-review',
  rewrite_done: 'rewrite-review',
  voice_selecting: 'tts-generate',
  tts_generating: 'tts-generate',
  tts_done: 'video-upload',
  video_uploading: 'video-upload',
  video_uploaded: 'video-upload',
  video_generating: 'generating',
  generating: 'generating',
  completed: 'video-preview',
  failed: 'task-list',
}

const stepPageMap = {
  script: 'script-input',
  rewrite: 'rewrite-review',
  tts: 'tts-generate',
  video: 'video-upload',
  generating: 'generating',
  preview: 'video-preview',
}

function resumePage() {
  if (props.task.status === 'completed') return 'video-preview'
  if (props.task.status === 'failed') {
    return props.task.current_step === 'generating'
      ? 'video-upload'
      : (stepPageMap[props.task.current_step] || 'script-input')
  }
  return statusPageMap[props.task.status] || stepPageMap[props.task.current_step] || 'script-input'
}

function viewResult() {
  setCurrentTask(props.task)
  if (props.task.status === 'completed') {
    navigate(resumePage())
  } else {
    navigate(resumePage())
  }
}

function continueEdit() {
  setCurrentTask(props.task)
  navigate(resumePage())
}
</script>

<template>
  <article class="card task-card" :data-task-id="task.id" role="button" tabindex="0" @click="continueEdit" @keydown.enter="continueEdit">
    <div class="task-main">
      <div class="task-summary">
        <span class="task-icon">
          <IconVideo v-if="task.status === 'completed'" :size="28" stroke-width="1.8" />
          <IconAlertTriangle v-else-if="task.status === 'failed'" :size="28" stroke-width="1.8" />
          <IconLoader v-else :size="28" stroke-width="1.8" />
        </span>
        <div class="task-copy">
          <strong class="task-title">{{ task.title || '未命名任务' }}</strong>
          <div class="task-meta">{{ displayTime }}<template v-if="displayDuration"> · {{ displayDuration }}</template></div>
          <div class="task-status-line" :class="statusInfo.class">
            <span />
            {{ statusInfo.label }}
          </div>
        </div>
      </div>
      <button
        v-if="task.status === 'completed'"
        class="task-btn"
        type="button"
        @click.stop="viewResult"
      >查看</button>
      <button
        v-else-if="task.status !== 'failed'"
        class="task-btn"
        type="button"
        @click.stop="continueEdit"
      >继续</button>
      <button
        v-else
        class="task-btn"
        type="button"
        @click.stop="continueEdit"
      >重试</button>
    </div>

    <div v-if="task.status === 'failed'" class="error-section">
      <div class="error-text">失败原因：{{ task.error_message }}</div>
      <div v-if="task.refund_status" class="refund-text">积分已退回（{{ task.point_cost }} 积分）</div>
    </div>

    <div class="card-bottom">
      <span class="text-xs muted cost-text">消耗 {{ task.point_cost }} 积分</span>
    </div>
  </article>
</template>

<style scoped>
.task-card {
  width: 100%;
  max-width: 100%;
  min-width: 0;
  min-height: 122px;
  padding: 18px;
  border-radius: 28px;
  overflow: hidden;
  cursor: pointer;
}

.task-main {
  width: 100%;
  min-width: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.task-summary {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1 1 auto;
  min-width: 0;
  overflow: hidden;
}

.task-copy {
  flex: 1 1 auto;
  min-width: 0;
}

.task-icon {
  width: 76px;
  height: 76px;
  display: grid;
  place-items: center;
  border-radius: 22px;
  background:
    radial-gradient(circle at 74% 18%, rgba(255, 209, 90, 0.16), transparent 28%),
    rgba(255, 255, 255, 0.07);
  flex-shrink: 0;
  color: var(--accent);
}

.task-title {
  max-width: 100%;
  font-size: 20px;
  font-weight: 700;
  display: block;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
  margin-bottom: 4px;
}

.task-meta {
  overflow: hidden;
  color: var(--muted);
  font-size: 12px;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.task-status-line {
  display: flex;
  align-items: center;
  gap: 7px;
  margin-top: 8px;
  font-size: 16px;
  font-weight: 800;
}

.task-status-line span {
  width: 9px;
  height: 9px;
  border-radius: 999px;
  background: currentColor;
}

.status-tag-success {
  color: var(--accent);
}

.status-tag-warning {
  color: var(--accent-2);
}

.status-tag-failed {
  color: var(--danger);
}

.error-section {
  margin-top: 12px;
}

.error-text {
  font-size: 14px;
  color: var(--danger);
}

.refund-text {
  font-size: 14px;
  color: var(--accent);
  margin-top: 4px;
}

.card-bottom {
  margin-top: 10px;
}

.cost-text {
  font-size: 13px;
}

.task-btn {
  flex: 0 0 auto;
  min-width: 68px;
  background: rgba(255, 255, 255, 0.06);
  color: var(--text);
  border: 1px solid var(--line-strong);
  border-radius: 999px;
  padding: 9px 14px;
  font-size: 15px;
  font-weight: 700;
}


@media (max-width: 360px) {
  .task-icon {
    width: 56px;
    height: 56px;
    border-radius: 18px;
  }

  .task-title {
    font-size: 17px;
  }
}
</style>
