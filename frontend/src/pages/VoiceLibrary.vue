<script setup>
import { onMounted, ref } from 'vue'
import { IconChevronLeft, IconPlayerPlay, IconPlayerStop, IconWaveSine } from '@tabler/icons-vue'
import { loadVoices, navigate, navigateToVoiceClone, state } from '../state/creationState.js'

onMounted(() => {
  loadVoices()
})

const activeVoiceId = ref(null)

function toggleVoice(voice) {
  if (!voice.sample_audio_url) return
  activeVoiceId.value = activeVoiceId.value === voice.id ? null : voice.id
}

function back() {
  navigate('create-home')
}
</script>

<template>
  <div>
    <header class="page-header">
      <button class="back-btn" type="button" @click="back">
        <IconChevronLeft :size="32" stroke-width="2" />
      </button>
      <h1>我的音色</h1>
      <button class="add-outline" type="button" @click="navigateToVoiceClone('voice-library')">新增</button>
    </header>

    <section class="voice-stat card">
      <IconWaveSine :size="62" stroke-width="1.75" />
      <div>
        <strong>已保存 <span>{{ state.voices.length }}</span> 个音色</strong>
        <p>可直接复用 voice_id</p>
      </div>
    </section>

    <section class="voice-list">
      <article v-for="voice in state.voices" :key="voice.id" class="voice-row card">
        <div class="voice-mark">
          <IconWaveSine :size="38" stroke-width="1.7" />
        </div>
        <div class="voice-copy">
          <strong>{{ voice.name }}</strong>
          <span>voice_id: {{ voice.provider_voice_id }}</span>
          <small>创建时间：{{ voice.created_at }}</small>
          <em><i />可用</em>
        </div>
        <div class="voice-actions">
          <button class="listen-btn" type="button" @click="toggleVoice(voice)">
            <component :is="activeVoiceId === voice.id ? IconPlayerStop : IconPlayerPlay" :size="28" stroke-width="1.8" />
            {{ activeVoiceId === voice.id ? '收起' : '试听' }}
          </button>
        </div>
        <audio
          v-if="activeVoiceId === voice.id"
          class="voice-player"
          :src="voice.sample_audio_url"
          controls
          preload="metadata"
        />
      </article>
    </section>
  </div>
</template>

<style scoped>
.add-outline {
  min-width: 72px;
  height: 44px;
  border-radius: 999px;
  color: var(--text);
  background:
    linear-gradient(var(--bg), var(--bg)) padding-box,
    linear-gradient(110deg, var(--accent), var(--accent-2)) border-box;
  border: 1px solid transparent;
  font-size: 16px;
  font-weight: 800;
}

.voice-stat {
  min-height: 154px;
  display: flex;
  align-items: center;
  gap: 18px;
  padding: 26px;
  border-color: rgba(53, 225, 192, 0.42);
  background:
    radial-gradient(circle at 100% 50%, rgba(255, 209, 90, 0.14), transparent 38%),
    radial-gradient(circle at 0% 50%, rgba(53, 225, 192, 0.14), transparent 36%),
    rgba(8, 15, 24, 0.88);
}

.voice-stat svg {
  color: var(--accent);
}

.voice-stat strong {
  display: block;
  font-size: 28px;
  letter-spacing: -0.05em;
}

.voice-stat strong span {
  color: var(--accent-2);
}

.voice-stat p {
  margin: 10px 0 0;
  color: var(--muted);
  font-size: 16px;
}

.voice-list {
  display: grid;
  gap: 14px;
  margin-top: 22px;
}

.voice-row {
  display: grid;
  grid-template-columns: 70px 1fr 74px;
  gap: 14px;
  align-items: center;
  min-height: 146px;
  padding: 18px;
}

.voice-mark {
  width: 66px;
  height: 66px;
  display: grid;
  place-items: center;
  border-radius: 999px;
  color: var(--accent);
  background: rgba(53, 225, 192, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.12);
}

.voice-copy {
  display: grid;
  gap: 6px;
  min-width: 0;
}

.voice-copy strong {
  font-size: 20px;
}

.voice-copy span,
.voice-copy small {
  overflow: hidden;
  color: var(--muted);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.voice-copy em {
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--accent);
  font-style: normal;
  font-weight: 800;
}

.voice-copy i {
  width: 9px;
  height: 9px;
  border-radius: 999px;
  background: var(--accent);
}

.voice-actions {
  display: grid;
}

.listen-btn {
  min-height: 74px;
  display: grid;
  justify-items: center;
  align-content: center;
  gap: 4px;
  border-radius: 18px;
  font-size: 14px;
  font-weight: 800;
}

.voice-player {
  grid-column: 1 / -1;
  width: 100%;
  display: block;
}

.listen-btn {
  color: var(--text);
  background: rgba(255, 255, 255, 0.07);
  border: 1px solid var(--line);
}
</style>
