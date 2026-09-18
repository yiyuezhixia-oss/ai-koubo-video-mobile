<script setup>
import { ref } from 'vue'
import {
  IconMicrophone2,
  IconPlayerPlay,
  IconPlayerStop,
  IconCheck,
} from '@tabler/icons-vue'

const props = defineProps({
  voice: {
    type: Object,
    required: true,
  },
})

const emit = defineEmits(['use'])

const showPlayer = ref(false)
const error = ref('')

function stopPlay() {
  showPlayer.value = false
}

function togglePlay() {
  if (!props.voice.sample_audio_url) {
    error.value = '这个音色暂时没有试听样音'
    return
  }

  error.value = ''
  showPlayer.value = !showPlayer.value
}

function useVoice() {
  stopPlay()
  emit('use', props.voice)
}
</script>

<template>
  <div class="card voice-card">
    <div class="flex-between">
      <div class="flex-row" style="gap: 12px; min-width: 0;">
        <span class="voice-icon">
          <IconMicrophone2 :size="22" stroke-width="1.8" />
        </span>
        <div style="min-width: 0;">
          <strong class="voice-name">{{ voice.name }}</strong>
          <div class="text-xs muted" style="margin-top: 4px;">
            {{ voice.provider_voice_id }} · {{ voice.created_at }}
          </div>
        </div>
      </div>
      <span class="badge badge-success">可用</span>
    </div>

    <p v-if="error" class="voice-error">{{ error }}</p>

    <div class="mt-16 flex-between" style="margin-top: 14px;">
      <button
        class="action-btn secondary"
        style="width: auto; height: 38px; padding: 0 16px; font-size: 14px;"
        type="button"
        @click="togglePlay"
      >
        <component :is="showPlayer ? IconPlayerStop : IconPlayerPlay" :size="18" stroke-width="2" />
        {{ showPlayer ? '收起' : '试听' }}
      </button>
      <button
        class="action-btn primary"
        style="width: auto; height: 38px; padding: 0 16px; font-size: 14px;"
        type="button"
        @click="useVoice"
      >
        <IconCheck :size="18" stroke-width="2" />
        使用
      </button>
    </div>
    <audio
      v-if="showPlayer && voice.sample_audio_url"
      class="voice-player"
      :src="voice.sample_audio_url"
      controls
      preload="metadata"
    />
  </div>
</template>

<style scoped>
.voice-icon {
  width: 44px;
  height: 44px;
  display: grid;
  place-items: center;
  border-radius: 12px;
  background: var(--card-strong);
  flex-shrink: 0;
}

.voice-name {
  font-size: 16px;
  font-weight: 600;
  display: block;
}

.voice-error {
  margin: 12px 0 0;
  color: var(--danger);
  font-size: 12px;
}

.voice-player {
  width: 100%;
  display: block;
  margin-top: 12px;
}
</style>
