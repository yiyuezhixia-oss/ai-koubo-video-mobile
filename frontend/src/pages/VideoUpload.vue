<script setup>
import { computed, ref } from 'vue'
import { IconArrowLeft } from '@tabler/icons-vue'
import { generateVideo, getPricing, uploadVideo } from '../api/mockApi.js'
import ActionButton from '../components/ActionButton.vue'
import PointCostHint from '../components/PointCostHint.vue'
import UploadCard from '../components/UploadCard.vue'
import { navigate, state, updateCurrentTask } from '../state/creationState.js'

const task = computed(() => state.currentTask)
const videoName = ref(task.value?.source_video_name || '')
const videoFile = ref(null)
const uploadedMedia = ref(task.value?.source_video_file || null)
const uploadStatus = ref(task.value?.source_video_file ? 'uploaded' : 'selected')
const uploading = ref(false)
const loading = ref(false)
const cost = ref(40)
const error = ref('')

const hasTts = computed(() => !!task.value?.tts_audio_url || !!task.value?.tts_audio_file)
const ttsAudioUrl = computed(() => task.value?.tts_audio_url || task.value?.tts_audio_file?.file_url || '')
const audioDuration = computed(() => Number(task.value?.tts_audio_file?.duration || 0))
const videoDuration = computed(() => Number(uploadedMedia.value?.duration || 0))
const audioTooLong = computed(() => videoDuration.value > 0 && audioDuration.value > videoDuration.value + 0.5)

function formatDuration(seconds) {
  if (!seconds) return '--'
  const minutes = Math.floor(seconds / 60)
  const rest = Math.round(seconds % 60).toString().padStart(2, '0')
  return `${minutes}:${rest}`
}

async function refreshCost() {
  try {
    const pricing = await getPricing({ duration_seconds: task.value?.tts_audio_file?.duration || 60 })
    cost.value = pricing.digital_human_points
  } catch {
    cost.value = 40
  }
}

refreshCost()

function goToTts() {
  navigate('tts-generate')
}

async function onVideoSelected(file) {
  videoFile.value = file
  uploadedMedia.value = null
  if (!file) {
    uploadStatus.value = 'selected'
    return
  }

  uploading.value = true
  uploadStatus.value = 'uploading'
  error.value = ''
  try {
    const uploaded = await uploadVideo(task.value.id, file, task.value?.tts_audio_file?.duration || 60)
    uploadedMedia.value = uploaded
    uploadStatus.value = 'uploaded'
    updateCurrentTask({
      source_video_name: uploaded.file_name || file.name,
      source_video_file: uploaded,
      status: 'video_uploaded',
    })
  } catch (e) {
    uploadStatus.value = 'selected'
    error.value = e.message || '视频上传失败，请重试'
  } finally {
    uploading.value = false
  }
}

async function doGenerate() {
  if (!uploadedMedia.value || !task.value?.id || audioTooLong.value) return
  loading.value = true
  error.value = ''
  try {
    const result = await generateVideo(task.value.id, `digital_human_${task.value.id}_${Date.now()}`)
    updateCurrentTask({
      output_video_url: result.output_video_url,
      output_video_file: result.output_video_file,
      point_cost: (task.value.point_cost || 0) + (result.point_cost || cost.value),
      status: result.status || 'generating',
      current_step: result.current_step || 'generating',
    })
    navigate('generating')
  } catch (e) {
    error.value = e.message || '生成成片失败，请重试'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div>
    <div class="page-header">
      <button class="back-btn" type="button" @click="navigate('tts-generate')">
        <IconArrowLeft :size="20" stroke-width="2" />
      </button>
      <h1>上传视频</h1>
      <span />
    </div>

    <div v-if="!hasTts" class="card" style="margin-bottom: 16px;">
      <p class="text-sm" style="margin: 0 0 12px;">还没有生成配音</p>
      <ActionButton variant="secondary" @click="goToTts">去生成配音</ActionButton>
    </div>

    <template v-else>
      <div class="card audio-review-card">
        <div class="text-xs muted">当前配音预览</div>
        <div class="text-sm">上传视频前，请再次试听确认配音内容和声音。</div>
        <audio v-if="ttsAudioUrl" class="audio-player" :src="ttsAudioUrl" controls preload="metadata" />
      </div>

      <div style="margin-bottom: 16px;">
        <div class="text-sm" style="margin-bottom: 10px;">上传视频素材</div>
        <UploadCard v-model="videoName" type="video" :status="uploadStatus" @file-selected="onVideoSelected" />
      </div>

      <p v-if="uploadStatus === 'uploaded'" class="upload-success">视频已上传到服务器，可以生成成片。</p>

      <div v-if="uploadStatus === 'uploaded'" class="duration-check" :class="{ invalid: audioTooLong }">
        <span>配音 {{ formatDuration(audioDuration) }}</span>
        <span>视频 {{ formatDuration(videoDuration) }}</span>
      </div>
      <p v-if="audioTooLong" class="error-text">
        配音比视频长 {{ (audioDuration - videoDuration).toFixed(1) }} 秒，请上传更长视频或缩短文案后重新生成配音。
      </p>
      <p v-else-if="uploadStatus === 'uploaded' && videoDuration > audioDuration" class="duration-note">
        成片将以配音时长为准，视频末尾多余部分不会进入成片。
      </p>

      <PointCostHint :cost="cost" />
      <p class="cost-note">按数字人预计时长计费：当前暂定 40 积分/分钟，不足 1 分钟按 1 分钟。</p>
      <p v-if="error" class="error-text">{{ error }}</p>

      <div class="mt-16">
        <ActionButton variant="primary" :disabled="!uploadedMedia || uploading || audioTooLong" :loading="loading || uploading" @click="doGenerate">
          生成成片
        </ActionButton>
      </div>
    </template>
  </div>
</template>

<style scoped>
.audio-review-card {
  margin-bottom: 16px;
}

.audio-review-card .text-sm {
  margin: 6px 0 12px;
  color: var(--text);
}

.audio-player {
  width: 100%;
  display: block;
}

.cost-note {
  margin: 10px 0 0;
  color: var(--muted);
  font-size: 13px;
  line-height: 1.5;
}

.upload-success {
  margin: -6px 0 14px;
  color: var(--accent);
  font-size: 13px;
}

.duration-check {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  margin: 0 0 12px;
  padding: 12px 14px;
  border: 1px solid rgba(53, 225, 192, 0.28);
  border-radius: 16px;
  color: var(--accent);
  background: rgba(53, 225, 192, 0.06);
  font-size: 13px;
  font-weight: 700;
}

.duration-check.invalid {
  color: var(--danger);
  border-color: rgba(255, 107, 107, 0.32);
  background: rgba(255, 107, 107, 0.06);
}

.duration-note {
  margin: 0 0 12px;
  color: var(--muted);
  font-size: 13px;
  line-height: 1.5;
}
</style>
