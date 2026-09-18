<script setup>
import { computed } from 'vue'
import { IconArrowLeft, IconDownload, IconPlus, IconRefresh } from '@tabler/icons-vue'
import ActionButton from '../components/ActionButton.vue'
import { navigate, state } from '../state/creationState.js'

const task = state.currentTask
const outputUrl = computed(() => task?.output_video_file?.file_url || '')
const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api'
const ACCESS_TOKEN_KEY = 'zhixia_access_token'

const downloadUrl = computed(() => {
  if (!task?.id || !outputUrl.value) return ''
  const token = localStorage.getItem(ACCESS_TOKEN_KEY) || ''
  const query = token ? `?access_token=${encodeURIComponent(token)}` : ''
  return `${API_BASE}/tasks/${task.id}/download-output/${query}`
})

function regenerate() {
  navigate('video-upload')
}

function makeNew() {
  state.currentTask = null
  navigate('create-home')
}
</script>

<template>
  <div>
    <div class="page-header">
      <button class="back-btn" type="button" @click="navigate('task-list')">
        <IconArrowLeft :size="20" stroke-width="2" />
      </button>
      <h1>成片预览</h1>
      <span />
    </div>

    <video v-if="outputUrl" class="video-preview" :src="outputUrl" controls playsinline preload="metadata" />
    <div v-else class="video-missing card">
      暂未获取到成片地址，请返回任务记录刷新状态。
    </div>

    <div class="card mt-20">
      <div class="text-xs muted" style="margin-bottom: 8px;">任务摘要</div>
      <div class="text-sm task-summary">
        <div>标题：{{ task?.title || '未命名任务' }}</div>
        <div>消耗积分：{{ task?.point_cost || 0 }} 积分</div>
        <div>状态：<span :class="task?.status === 'completed' ? 'success' : 'muted'">{{ task?.status === 'completed' ? '已完成' : '处理中' }}</span></div>
      </div>
    </div>

    <div class="preview-actions mt-24">
      <a v-if="downloadUrl" class="download-link" :href="downloadUrl" download>
        <IconDownload :size="20" stroke-width="2" />
        下载成片
      </a>
      <ActionButton v-else variant="primary" disabled>下载成片</ActionButton>
      <ActionButton variant="secondary" @click="regenerate">
        <IconRefresh :size="20" stroke-width="2" />
        重新生成
      </ActionButton>
      <ActionButton variant="secondary" @click="makeNew">
        <IconPlus :size="20" stroke-width="2" />
        再做一个
      </ActionButton>
    </div>
  </div>
</template>

<style scoped>
.video-preview {
  width: 100%;
  max-height: 480px;
  display: block;
  border-radius: 22px;
  background: #000;
  border: 1px solid var(--line);
}

.video-missing {
  padding: 32px 20px;
  color: var(--muted);
  text-align: center;
  line-height: 1.6;
}

.task-summary {
  line-height: 1.8;
}

.success {
  color: var(--accent);
}

.preview-actions {
  display: grid;
  gap: 10px;
}

.download-link {
  min-height: 58px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  border-radius: 999px;
  color: #081016;
  background: linear-gradient(100deg, var(--accent), #86d99b 48%, var(--accent-2));
  border: 0;
  font-size: 18px;
  font-weight: 900;
  font-family: inherit;
  text-decoration: none;
  cursor: pointer;
}
</style>
