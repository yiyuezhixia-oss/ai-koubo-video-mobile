<script setup>
import { ref } from 'vue'
import { IconChevronLeft, IconCloudUpload, IconMicrophone2, IconPlayerPlay, IconRefresh } from '@tabler/icons-vue'
import { confirmVoice, discardVoice, previewCloneVoice } from '../api/mockApi.js'
import LoadingOverlay from '../components/LoadingOverlay.vue'
import PointCostHint from '../components/PointCostHint.vue'
import { loadVoices, navigate, state, updateCurrentTask } from '../state/creationState.js'

const audioFile = ref(null)
const voiceName = ref('')
const cloneTestText = ref('你好，我是你的 AI 口播音色。')
const loading = ref(false)
const playing = ref(false)
const error = ref('')
const message = ref('')
const ownershipConfirmed = ref(false)
const separateConsentConfirmed = ref(false)

function onFileChange(event) {
  const file = event.target.files?.[0]
  if (!file) return
  audioFile.value = file
  state.pendingVoice = null
  error.value = ''
  message.value = ''
}

function triggerUpload() {
  document.getElementById('audio-input')?.click()
}

function validate() {
  if (!audioFile.value) return '请先上传一段音频'
  if (!voiceName.value.trim()) return '请给这个音色取个名字'
  if (!cloneTestText.value.trim()) return '请填写一段克隆后试听文案'
  if (cloneTestText.value.trim().length > 200) return '试听文案不能超过 200 字'
  if (!ownershipConfirmed.value || !separateConsentConfirmed.value) return '请完成两项声音授权确认'
  return ''
}

async function createPreview() {
  const problem = validate()
  if (problem) {
    error.value = problem
    return
  }

  loading.value = true
  error.value = ''
  message.value = ''
  try {
    state.pendingVoice = await previewCloneVoice(
      audioFile.value,
      voiceName.value.trim(),
      cloneTestText.value.trim(),
      {
        ownershipConfirmed: ownershipConfirmed.value,
        separateConsentConfirmed: separateConsentConfirmed.value,
      },
      `voice_preview_${Date.now()}`,
    )
    message.value = '试听音频已生成，确认满意后再入库扣积分'
  } catch (e) {
    error.value = e.message || '生成试听失败，请重试'
  } finally {
    loading.value = false
  }
}

function togglePreview() {
  if (!state.pendingVoice?.sample_audio_url) return
  playing.value = !playing.value
  if (playing.value) {
    setTimeout(() => {
      playing.value = false
    }, 1800)
  }
}

async function retryPreview() {
  if (state.pendingVoice?.id) {
    await discardVoice(state.pendingVoice.id).catch(() => {})
  }
  state.pendingVoice = null
  message.value = '已丢弃本次试听，可重新生成'
}

async function confirmAndSave() {
  if (!state.pendingVoice?.id) {
    error.value = '请先生成试听音频'
    return
  }
  loading.value = true
  error.value = ''
  try {
    const voice = await confirmVoice(state.pendingVoice.id, `voice_confirm_${Date.now()}`)
    await loadVoices()
    if (state.cloneReturnPage === 'tts-generate' && state.currentTask) {
      updateCurrentTask({
        selected_voice_id: voice.id,
        tts_audio_url: null,
      })
    }
    state.pendingVoice = null
    navigate(state.cloneReturnPage || 'voice-library')
  } catch (e) {
    error.value = e.message || '确认入库失败，请检查积分余额'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div>
    <header class="page-header">
      <button class="back-btn" type="button" @click="navigate(state.cloneReturnPage || 'voice-library')">
        <IconChevronLeft :size="32" stroke-width="2" />
      </button>
      <h1>克隆音色</h1>
      <span />
    </header>

    <section class="clone-hero card">
      <div class="clone-icon">
        <IconMicrophone2 :size="72" stroke-width="1.55" />
      </div>
      <h2>上传 <span>10</span> 秒以上音频</h2>
      <p>先生成试听，不满意不入库、不扣确认积分</p>
      <button class="upload-pill" type="button" @click="triggerUpload">
        <IconCloudUpload :size="22" stroke-width="1.8" />
        点击上传文件
      </button>
      <strong v-if="audioFile" class="file-name">{{ audioFile.name }}</strong>
    </section>

    <label class="field-block">
      <span>音色名称</span>
      <input v-model="voiceName" type="text" placeholder="例如：温柔讲解女声" />
    </label>

    <label class="field-block">
      <span>试听文案</span>
      <textarea
        v-model="cloneTestText"
        maxlength="200"
        rows="4"
        placeholder="克隆完成后用这段文案生成试听音频，最多 200 字"
      />
      <small>{{ cloneTestText.length }}/200</small>
    </label>

    <section class="save-hint card">
      <IconMicrophone2 :size="32" stroke-width="1.7" />
      <p>生成试听不扣 199 积分；点击“确认入库”后才保存 voice_id，并提醒 7 天内使用一次该音色。</p>
    </section>

    <section class="authorization-card card">
      <h3>声音授权确认</h3>
      <p>声音属于敏感个人信息。请在上传前确认来源合法，禁止冒充他人或未经许可克隆他人声音。</p>
      <label>
        <input v-model="ownershipConfirmed" type="checkbox" />
        <span>这是我本人的声音，或我已获得声音权利人的明确授权。</span>
      </label>
      <label>
        <input v-model="separateConsentConfirmed" type="checkbox" />
        <span>我已告知被编辑者用途、保存方式及风险，并取得其单独同意。</span>
      </label>
      <small>提交后将记录账号、声明版本、时间、IP 和客户端信息，用于处理争议和保护权利人。</small>
    </section>

    <section v-if="state.pendingVoice" class="preview-card card">
      <div>
        <strong>{{ state.pendingVoice.name }}</strong>
        <span>试听已生成，voice_id 待确认入库</span>
      </div>
      <button class="listen-btn" type="button" @click="togglePreview">
        <IconPlayerPlay :size="24" stroke-width="1.8" />
        {{ playing ? '试听中' : '试听' }}
      </button>
    </section>

    <p v-if="message" class="success-text">{{ message }}</p>
    <p v-if="error" class="error-text">{{ error }}</p>

    <div class="clone-action">
      <button
        v-if="!state.pendingVoice"
        class="action-btn primary"
        :disabled="!audioFile || !voiceName.trim() || !cloneTestText.trim() || cloneTestText.trim().length > 200 || !ownershipConfirmed || !separateConsentConfirmed || loading"
        type="button"
        @click="createPreview"
      >
        生成试听
      </button>

      <template v-else>
        <PointCostHint :cost="199" label="确认入库消耗" />
        <button class="action-btn primary" :disabled="loading" type="button" @click="confirmAndSave">
          确认入库
        </button>
        <button class="action-btn secondary" :disabled="loading" type="button" @click="retryPreview">
          <IconRefresh :size="20" stroke-width="2" />
          不满意，重来
        </button>
      </template>
    </div>

    <input id="audio-input" type="file" accept="audio/*" hidden @change="onFileChange" />
    <LoadingOverlay v-if="loading" text="处理中..." />
  </div>
</template>

<style scoped>
.clone-hero {
  padding: 34px 18px;
  text-align: center;
  border-color: rgba(53, 225, 192, 0.36);
  background:
    radial-gradient(circle at 50% 0%, rgba(53, 225, 192, 0.13), transparent 38%),
    rgba(8, 15, 24, 0.86);
}

.clone-icon {
  display: grid;
  place-items: center;
  margin-bottom: 12px;
  color: var(--text);
}

.clone-hero h2 {
  margin: 0;
  font-size: 26px;
  letter-spacing: -0.04em;
}

.clone-hero h2 span {
  color: var(--accent-2);
}

.clone-hero p {
  margin: 8px 0 18px;
  color: var(--muted);
}

.upload-pill {
  min-height: 48px;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 0 20px;
  border-radius: 999px;
  color: var(--text);
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid var(--line);
  font-weight: 800;
}

.file-name {
  display: block;
  margin-top: 12px;
  color: var(--accent);
  font-size: 13px;
}

.field-block {
  display: grid;
  gap: 10px;
  margin-top: 18px;
}

.field-block span {
  font-size: 16px;
  font-weight: 800;
}

.field-block input,
.field-block textarea {
  width: 100%;
  min-height: 58px;
  padding: 16px 18px;
  outline: none;
  border: 1px solid var(--line);
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.06);
}

.field-block textarea {
  resize: none;
  line-height: 1.55;
}

.field-block small {
  justify-self: end;
  color: var(--muted);
}

.save-hint,
.preview-card {
  display: flex;
  gap: 12px;
  align-items: center;
  margin-top: 16px;
  color: var(--muted-strong);
}

.authorization-card {
  display: grid;
  gap: 13px;
  margin-top: 16px;
}

.authorization-card h3,
.authorization-card p {
  margin: 0;
}

.authorization-card p,
.authorization-card small {
  color: var(--muted);
  line-height: 1.55;
}

.authorization-card label {
  display: grid;
  grid-template-columns: 22px 1fr;
  gap: 10px;
  align-items: start;
  color: var(--muted-strong);
  line-height: 1.5;
}

.authorization-card input {
  width: 20px;
  height: 20px;
  accent-color: var(--accent);
}

.save-hint svg {
  color: var(--accent);
  flex: 0 0 auto;
}

.save-hint p {
  margin: 0;
  font-size: 14px;
  line-height: 1.55;
}

.preview-card {
  justify-content: space-between;
  border-color: rgba(53, 225, 192, 0.32);
}

.preview-card strong,
.preview-card span {
  display: block;
}

.preview-card span {
  margin-top: 4px;
  color: var(--muted);
  font-size: 13px;
}

.listen-btn {
  min-width: 80px;
  min-height: 58px;
  display: grid;
  justify-items: center;
  align-content: center;
  gap: 3px;
  border-radius: 18px;
  color: var(--text);
  background: rgba(255, 255, 255, 0.07);
  border: 1px solid var(--line);
  font-size: 13px;
  font-weight: 800;
}

.success-text {
  margin: 12px 0 0;
  color: var(--accent);
  font-size: 13px;
  font-weight: 800;
}

.clone-action {
  display: grid;
  gap: 12px;
  margin-top: 22px;
}
</style>
