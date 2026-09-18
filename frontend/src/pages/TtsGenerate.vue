<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import {
  IconArrowLeft,
  IconMicrophone2,
  IconPlayerPlay,
  IconPlayerStop,
  IconPlus,
} from '@tabler/icons-vue'
import { generateTts, getPricing } from '../api/mockApi.js'
import { loadVoices, navigate, navigateToVoiceClone, state, updateCurrentTask } from '../state/creationState.js'
import ActionButton from '../components/ActionButton.vue'
import PointCostHint from '../components/PointCostHint.vue'

const loading = ref(false)
const showVoicePlayer = ref(false)
const error = ref('')
const ttsCost = ref(0)
const maxChars = ref(2000)
const pitch = ref(0)
const speed = ref(1)
const volume = ref(1)
const emotion = ref('')

const emotions = [
  { value: '', label: '自动' },
  { value: 'happy', label: '开心' },
  { value: 'sad', label: '悲伤' },
  { value: 'angry', label: '愤怒' },
  { value: 'fearful', label: '恐惧' },
  { value: 'disgusted', label: '厌恶' },
  { value: 'surprised', label: '惊讶' },
  { value: 'calm', label: '平静' },
]

const task = computed(() => state.currentTask)
const selectedVoice = computed(() =>
  state.voices.find((voice) => String(voice.id) === String(task.value?.selected_voice_id)) || null,
)
const ttsGenerated = computed(() => !!task.value?.tts_audio_url)
const scriptLength = computed(() => (task.value?.rewritten_text || '').length)

onMounted(async () => {
  await loadVoices()
  await refreshCost()
})

onBeforeUnmount(() => {
  stopPreview()
})

async function refreshCost() {
  try {
    const pricing = await getPricing({ text: task.value?.rewritten_text || '' })
    ttsCost.value = pricing.tts_points
    maxChars.value = pricing.tts_max_chars
  } catch {
    ttsCost.value = 0
  }
}

function changeVoice(event) {
  stopPreview()
  showVoicePlayer.value = false
  const voiceId = event.target.value || null
  updateCurrentTask({
    selected_voice_id: voiceId,
    tts_audio_url: null,
  })
  error.value = ''
}

function goClone() {
  stopPreview()
  navigateToVoiceClone('tts-generate')
}

function stopPreview() {
  showVoicePlayer.value = false
}

function toggleVoicePreview() {
  if (!selectedVoice.value) {
    error.value = '请先选择一个音色'
    return
  }

  if (!selectedVoice.value.sample_audio_url) {
    error.value = '该音色暂无试听样音；生成配音后可以在本页直接预览成品配音。'
    return
  }
  error.value = ''
  showVoicePlayer.value = !showVoicePlayer.value
}

async function doGenerateTts() {
  if (!task.value?.selected_voice_id) {
    error.value = '请先选择音色'
    return
  }
  if (!task.value?.rewritten_text) {
    error.value = '缺少配音文案，请返回确认 AI 改写文案'
    return
  }
  if (task.value.rewritten_text.length > maxChars.value) {
    error.value = `TTS 文案不能超过 ${maxChars.value} 字`
    return
  }

  stopPreview()
  loading.value = true
  error.value = ''
  const key = `tts_${task.value.id}_${Date.now()}`
  try {
    const result = await generateTts(
      task.value.id,
      task.value.selected_voice_id,
      task.value.rewritten_text,
      { pitch: pitch.value, speed: speed.value, volume: volume.value, emotion: emotion.value },
      key,
    )
    updateCurrentTask({
      tts_audio_url: result.tts_audio_url,
      tts_audio_file: result.tts_audio_file,
      point_cost: (task.value.point_cost || 0) + result.point_cost,
      status: 'tts_done',
      current_step: 'video',
    })
  } catch (e) {
    error.value = e.message || '生成配音失败，请重试'
  } finally {
    loading.value = false
  }
}

function nextStep() {
  if (!ttsGenerated.value) return
  stopPreview()
  navigate('video-upload')
}
</script>

<template>
  <div>
    <div class="page-header">
      <button class="back-btn" type="button" @click="navigate('rewrite-review')">
        <IconArrowLeft :size="26" stroke-width="2" />
      </button>
      <h1>生成配音</h1>
      <span />
    </div>

    <section class="voice-select-card card">
      <div class="voice-select-head">
        <div class="voice-icon">
          <IconMicrophone2 :size="28" stroke-width="1.8" />
        </div>
        <div>
          <strong>{{ selectedVoice?.name || '选择配音音色' }}</strong>
          <p>{{ selectedVoice ? `voice_id: ${selectedVoice.provider_voice_id}` : '从音色库中选择一个可复用音色' }}</p>
        </div>
      </div>

      <div class="select-row">
        <select :value="task?.selected_voice_id || ''" @change="changeVoice">
          <option value="">请选择音色</option>
          <option v-for="voice in state.voices" :key="voice.id" :value="voice.id">
            {{ voice.name }}
          </option>
        </select>
        <button class="clone-link" type="button" @click="goClone">
          <IconPlus :size="18" stroke-width="2" />
          前往克隆
        </button>
      </div>
    </section>

    <section class="card voice-params">
      <div class="params-title">声音参数</div>
      <label>
        <span>语速 <b>{{ speed.toFixed(1) }}x</b></span>
        <input v-model.number="speed" type="range" min="0.5" max="2" step="0.1" />
      </label>
      <label>
        <span>音调 <b>{{ pitch > 0 ? `+${pitch}` : pitch }}</b></span>
        <input v-model.number="pitch" type="range" min="-12" max="12" step="1" />
      </label>
      <label>
        <span>音量 <b>{{ volume.toFixed(1) }}</b></span>
        <input v-model.number="volume" type="range" min="0.1" max="2" step="0.1" />
      </label>
      <label>
        <span>情绪</span>
        <select v-model="emotion" aria-label="配音情绪">
          <option v-for="item in emotions" :key="item.value || 'auto'" :value="item.value">
            {{ item.label }}
          </option>
        </select>
      </label>
      <small>情绪仅对支持该能力的音色模型生效；“自动”不向工作流传入 emotion。</small>
    </section>

    <section class="card script-preview">
      <div class="script-preview-head">
        <div class="text-xs muted">配音文案</div>
        <span>{{ scriptLength }}/{{ maxChars }}</span>
      </div>
      <p>{{ task?.rewritten_text || '暂无文案，请先确认 AI 改写内容' }}</p>
    </section>

    <button
      class="action-btn secondary"
      style="margin-top: 16px;"
      type="button"
      :disabled="!selectedVoice"
      @click="toggleVoicePreview"
    >
      <component :is="showVoicePlayer ? IconPlayerStop : IconPlayerPlay" :size="20" stroke-width="2" />
      {{ showVoicePlayer ? '收起试听' : '试听音色' }}
    </button>
    <audio
      v-if="showVoicePlayer && selectedVoice?.sample_audio_url"
      class="voice-audio-player"
      :src="selectedVoice.sample_audio_url"
      controls
      preload="metadata"
    />

    <p v-if="error" class="error-text mt-12">{{ error }}</p>

    <div class="mt-16">
      <PointCostHint :cost="ttsCost" />
    </div>

    <div class="mt-16">
      <ActionButton
        v-if="!ttsGenerated"
        variant="primary"
        :disabled="!selectedVoice || loading"
        :loading="loading"
        @click="doGenerateTts"
      >
        生成配音
      </ActionButton>
      <template v-else>
        <div class="generated-card card">
          <div>
            <strong>配音已生成</strong>
            <p>请先试听确认；不满意可以调整音色、情绪或声音参数后重新生成。</p>
          </div>
          <audio class="tts-audio-player" :src="task.tts_audio_url" controls preload="metadata" />
        </div>
        <div class="regenerate-block">
          <p>重新生成会覆盖当前配音，并再次消耗 {{ ttsCost }} 积分。</p>
          <ActionButton variant="secondary" :disabled="loading" :loading="loading" @click="doGenerateTts">
            重新生成配音
          </ActionButton>
        </div>
        <ActionButton variant="primary" @click="nextStep">
          下一步，上传视频
        </ActionButton>
      </template>
    </div>
  </div>
</template>

<style scoped>
.voice-select-card {
  padding: 22px;
}

.voice-select-head {
  display: flex;
  gap: 14px;
  align-items: center;
}

.voice-icon {
  width: 58px;
  height: 58px;
  display: grid;
  place-items: center;
  flex: 0 0 auto;
  border-radius: 18px;
  color: var(--accent);
  background: rgba(255, 255, 255, 0.08);
}

.voice-select-head strong {
  display: block;
  font-size: 22px;
  letter-spacing: -0.03em;
}

.voice-select-head p {
  margin: 5px 0 0;
  color: var(--muted);
  font-size: 13px;
}

.select-row {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 10px;
  margin-top: 18px;
}

select {
  min-width: 0;
  height: 52px;
  padding: 0 14px;
  border-radius: 18px;
  outline: none;
  color: var(--text);
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid var(--line);
}

select option {
  color: #111827;
}

.clone-link {
  height: 52px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 0 14px;
  border-radius: 18px;
  color: #061018;
  background: linear-gradient(100deg, var(--accent), var(--accent-2));
  font-weight: 800;
}

.script-preview {
  margin-top: 16px;
  padding: 22px;
}

.voice-params {
  margin-top: 16px;
  padding: 20px 22px;
}

.params-title {
  margin-bottom: 14px;
  font-size: 15px;
  font-weight: 800;
}

.voice-params label {
  display: grid;
  grid-template-columns: 86px 1fr;
  align-items: center;
  gap: 12px;
  margin-top: 12px;
  color: var(--muted);
  font-size: 13px;
}

.voice-params b {
  color: var(--text);
  font-weight: 700;
}

.voice-params input {
  width: 100%;
  accent-color: var(--accent);
}

.voice-params select {
  width: 100%;
  height: 42px;
  border-radius: 14px;
}

.voice-params small {
  display: block;
  margin-top: 12px;
  color: var(--muted);
  line-height: 1.5;
}

.script-preview-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  color: var(--muted);
  font-size: 12px;
}

.script-preview p {
  margin: 10px 0 0;
  font-size: 17px;
  line-height: 1.78;
}

.generated-card {
  margin-bottom: 12px;
  color: var(--text);
  border-color: rgba(53, 225, 192, 0.34);
}

.generated-card strong {
  color: var(--accent);
  font-size: 18px;
}

.generated-card p {
  margin: 6px 0 14px;
  color: var(--muted);
  font-size: 13px;
}

.tts-audio-player {
  width: 100%;
  display: block;
}

.voice-audio-player {
  width: 100%;
  display: block;
  margin-top: 10px;
}

.regenerate-block {
  display: grid;
  gap: 10px;
  margin-bottom: 12px;
}

.regenerate-block p {
  margin: 0;
  color: var(--accent-2);
  font-size: 13px;
  line-height: 1.5;
  text-align: center;
}
</style>
