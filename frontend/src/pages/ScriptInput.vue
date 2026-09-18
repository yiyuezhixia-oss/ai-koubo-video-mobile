<script setup>
import { computed, ref } from 'vue'
import { IconChevronLeft } from '@tabler/icons-vue'
import { createTask } from '../api/mockApi.js'
import PointCostHint from '../components/PointCostHint.vue'
import { navigate, setCurrentTask } from '../state/creationState.js'

const scriptText = ref('')
const requirement = ref('')
const error = ref('')
const loading = ref(false)
const charCount = computed(() => scriptText.value.length)

function pasteDemo() {
  scriptText.value = '我以前总觉得学校的早八和晚自习很难熬，直到参加社团和比赛，才发现身边有许多愿意互相鼓励的朋友。那些忙碌的日子，也慢慢变成了我最珍贵的成长经历。'
  error.value = ''
}

function clearText() {
  scriptText.value = ''
  error.value = ''
}

async function nextStep() {
  if (!scriptText.value.trim()) {
    error.value = '请先粘贴视频原文或字幕'
    return
  }

  const rawInput = scriptText.value.trim()
  if (/https?:\/\//i.test(rawInput)) {
    error.value = '请粘贴视频原文或字幕，当前版本不解析抖音链接'
    return
  }

  loading.value = true
  error.value = ''
  try {
    const task = await createTask(rawInput, {
      source_type: 'manual',
    })
    task.rewrite_requirement = requirement.value.trim()
    setCurrentTask(task)
    navigate('rewrite-review')
  } catch (e) {
    error.value = e.message || '创建任务失败，请重试'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div>
    <header class="page-header">
      <button class="back-btn" type="button" @click="navigate('create-home')">
        <IconChevronLeft :size="32" stroke-width="2" />
      </button>
      <h1>文案输入</h1>
      <span />
    </header>

    <section class="script-box card">
      <textarea
        v-model="scriptText"
        maxlength="2000"
        placeholder="粘贴视频原文或字幕，AI 将改写为口播文案"
      />
      <span class="count">{{ charCount }}/2000</span>
    </section>

    <label class="requirement-box card">
      <span>改写需求（可选）</span>
      <input
        v-model="requirement"
        type="text"
        placeholder="例如：更像真人口播、语气更有销售感、保留核心卖点"
      />
    </label>

    <div class="input-actions">
      <button class="mini-btn" type="button" @click="pasteDemo">粘贴示例</button>
      <button class="mini-btn" type="button" @click="clearText">清空</button>
    </div>

    <p v-if="error" class="error-text">{{ error }}</p>

    <div class="fixed-action">
      <PointCostHint :cost="1" />
      <button class="action-btn primary" :disabled="!scriptText.trim() || loading" type="button" @click="nextStep">
        {{ loading ? '创建中...' : '下一步' }}
      </button>
    </div>
  </div>
</template>

<style scoped>
.script-box {
  min-height: 540px;
  padding: 24px;
}

textarea {
  width: 100%;
  min-height: 456px;
  resize: none;
  outline: none;
  border: 0;
  background: transparent;
  color: var(--text);
  font-size: 19px;
  line-height: 1.72;
}

.count {
  position: absolute;
  right: 22px;
  bottom: 18px;
  color: var(--muted);
  font-size: 15px;
}

.input-actions {
  display: flex;
  gap: 10px;
  margin-top: 14px;
}

.requirement-box {
  display: grid;
  gap: 10px;
  margin-top: 14px;
}

.requirement-box span {
  color: var(--muted-strong);
  font-size: 14px;
  font-weight: 800;
}

.requirement-box input {
  width: 100%;
  min-height: 50px;
  padding: 0 14px;
  outline: none;
  border: 1px solid var(--line);
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.06);
}

.mini-btn {
  height: 38px;
  padding: 0 14px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.07);
  color: var(--muted-strong);
  border: 1px solid var(--line);
}

.fixed-action {
  display: grid;
  gap: 12px;
  margin-top: 22px;
}
</style>
