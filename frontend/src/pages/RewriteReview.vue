<script setup>
import { onMounted, ref, watch } from 'vue'
import { IconChevronLeft, IconCircleCheck, IconReload, IconSparkles } from '@tabler/icons-vue'
import { navigate, state, updateCurrentTask } from '../state/creationState.js'
import { rewriteScript } from '../api/mockApi.js'
import PointCostHint from '../components/PointCostHint.vue'
import LoadingOverlay from '../components/LoadingOverlay.vue'

const loading = ref(false)
const error = ref('')
const editedText = ref('')

async function doRewrite() {
  if (!state.currentTask?.original_text) {
    navigate('script-input')
    return
  }

  loading.value = true
  error.value = ''
  try {
    const result = await rewriteScript(
      state.currentTask.id,
      state.currentTask.original_text,
      `rewrite_${state.currentTask.id}_${Date.now()}`,
      state.currentTask.rewrite_requirement || '',
    )
    updateCurrentTask({
      ...result,
      status: result.status || 'rewrite_done',
      point_cost: (state.currentTask.point_cost || 0) + (result.point_cost || 0),
      rewrite_requirement: state.currentTask.rewrite_requirement || '',
    })
    editedText.value = result.rewritten_text || ''
  } catch (e) {
    error.value = e.message || '改写失败，请重试'
  } finally {
    loading.value = false
  }
}

function confirmUse() {
  const finalText = editedText.value.trim()
  if (!finalText) return
  updateCurrentTask({
    rewritten_text: finalText,
    status: 'tts_generating',
    current_step: 'tts',
  })
  navigate('tts-generate')
}

watch(
  () => state.currentTask?.rewritten_text,
  (value) => {
    editedText.value = value || ''
  },
)

onMounted(() => {
  if (!state.currentTask) {
    navigate('script-input')
    return
  }
  if (!state.currentTask.rewritten_text) {
    doRewrite()
  } else {
    editedText.value = state.currentTask.rewritten_text
  }
})
</script>

<template>
  <div>
    <header class="page-header">
      <button class="back-btn" type="button" @click="navigate('script-input')">
        <IconChevronLeft :size="32" stroke-width="2" />
      </button>
      <h1>AI 改写确认</h1>
      <span />
    </header>

    <section class="copy-card card">
      <div class="copy-label">原始文案</div>
      <p>{{ state.currentTask?.original_text }}</p>
    </section>

    <section class="rewrite-card card">
      <div class="rewrite-title">
        <IconSparkles :size="30" stroke-width="1.7" />
        <strong>改写结果</strong>
      </div>
      <p v-if="loading" class="muted">AI 正在优化文案...</p>
      <textarea
        v-else-if="state.currentTask?.rewritten_text"
        v-model="editedText"
        class="rewrite-editor"
        maxlength="2000"
        placeholder="你可以在这里人工修改最终用于配音的文案"
      />
      <p v-else class="muted">点击重新改写生成内容</p>
    </section>

    <p v-if="error" class="error-text">{{ error }}</p>

    <div class="rewrite-actions">
      <button class="action-btn secondary" type="button" :disabled="loading" @click="doRewrite">
        <IconReload :size="22" stroke-width="2" />
        重新改写
      </button>
      <button
        class="action-btn primary"
        type="button"
        :disabled="!editedText.trim() || loading"
        @click="confirmUse"
      >
        <IconCircleCheck :size="22" stroke-width="2" />
        确认使用
      </button>
    </div>

    <div class="mt-12">
      <PointCostHint :cost="1" />
    </div>

    <LoadingOverlay v-if="loading" text="AI 正在改写中..." />
  </div>
</template>

<style scoped>
.copy-card,
.rewrite-card {
  padding: 22px;
}

.copy-label {
  margin-bottom: 12px;
  color: var(--muted);
  font-size: 14px;
  font-weight: 800;
}

.copy-card p,
.rewrite-card p {
  margin: 0;
  color: var(--muted-strong);
  font-size: 16px;
  line-height: 1.78;
}

.rewrite-card {
  margin-top: 16px;
  border-color: rgba(53, 225, 192, 0.32);
  background:
    radial-gradient(circle at 100% 0%, rgba(255, 209, 90, 0.12), transparent 36%),
    radial-gradient(circle at 0% 100%, rgba(53, 225, 192, 0.12), transparent 34%),
    rgba(8, 15, 24, 0.88);
}

.rewrite-title {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 14px;
  color: var(--accent);
  font-size: 22px;
}

.rewrite-card p:not(.muted) {
  color: var(--text);
  font-size: 18px;
}

.rewrite-editor {
  width: 100%;
  min-height: 320px;
  resize: vertical;
  border: 0;
  outline: none;
  color: var(--text);
  background: transparent;
  font-size: 18px;
  line-height: 1.78;
}

.rewrite-actions {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-top: 22px;
}
</style>
