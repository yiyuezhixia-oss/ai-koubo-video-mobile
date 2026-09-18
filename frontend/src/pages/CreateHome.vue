<script setup>
import {
  IconDots,
  IconHelpCircle,
  IconMicrophone2,
  IconPlus,
  IconSearch,
  IconWand,
  IconClipboardText,
} from '@tabler/icons-vue'
import { computed, onMounted } from 'vue'
import { loadTasks, loadUser, navigate, state } from '../state/creationState.js'

onMounted(() => {
  loadUser()
  loadTasks()
})

function startCreate() {
  navigate('script-input')
}

const recentTask = computed(() => state.tasks[0] || null)
const statusLabels = {
  draft: '草稿',
  rewriting: '改写中',
  rewrite_done: '待生成配音',
  tts_done: '待上传视频',
  video_uploaded: '视频已上传',
  generating: '生成中',
  completed: '生成完成',
  failed: '生成失败',
}
const recentStatus = computed(() => statusLabels[recentTask.value?.status] || recentTask.value?.status || '未知状态')
const recentDuration = computed(() => {
  const seconds = Math.max(0, Math.round(
    recentTask.value?.source_video_file?.duration
      || recentTask.value?.tts_audio_file?.duration
      || 0,
  ))
  return `${String(Math.floor(seconds / 60)).padStart(2, '0')}:${String(seconds % 60).padStart(2, '0')}`
})
</script>

<template>
  <div class="home-page">
    <header class="home-toolbar">
      <button class="icon-btn" type="button" aria-label="搜索">
        <IconSearch :size="32" stroke-width="1.8" />
      </button>
      <div class="home-toolbar-right">
        <button class="icon-btn" type="button" aria-label="帮助">
          <IconHelpCircle :size="30" stroke-width="1.8" />
        </button>
        <button class="icon-btn" type="button" aria-label="更多">
          <IconDots :size="30" stroke-width="1.8" />
        </button>
      </div>
    </header>

    <button class="hero-create gradient-panel" type="button" @click="startCreate">
      <span class="hero-plus">
        <IconPlus :size="42" stroke-width="2.1" />
      </span>
      <span class="hero-title">开始创作</span>
      <span class="hero-subtitle">文案、音色、视频一条线完成</span>
    </button>

    <section class="home-shortcuts">
      <button class="shortcut-card card" type="button" @click="navigate('task-list')">
        <IconClipboardText :size="54" stroke-width="1.65" />
        <strong>继续任务</strong>
        <span>从上次进度继续创作</span>
      </button>

      <button class="shortcut-card card" type="button" @click="navigate('voice-library')">
        <IconMicrophone2 :size="54" stroke-width="1.65" />
        <strong>我的音色</strong>
        <span>管理你定制的音色</span>
      </button>
    </section>

    <section class="recent-section">
      <h2>最近任务</h2>
      <button
        v-if="state.tasks.length"
        class="recent-task card"
        type="button"
        @click="navigate('task-list')"
      >
        <span class="recent-thumb">
          <IconMicrophone2 :size="48" stroke-width="1.6" />
          <small>{{ recentDuration }}</small>
        </span>
        <span class="recent-copy">
          <strong>{{ recentTask.title }}</strong>
          <em>{{ recentStatus }}</em>
          <small>最近更新</small>
        </span>
        <span class="recent-more">
          <IconDots :size="28" stroke-width="2" />
        </span>
      </button>
      <div v-else class="card empty-recent">
        <IconWand :size="34" stroke-width="1.7" />
        <span>还没有任务，先开始创作一个吧</span>
      </div>
    </section>
  </div>
</template>

<style scoped>
.home-page {
  padding-top: 8px;
}

.home-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 54px;
}

.home-toolbar-right {
  display: flex;
  gap: 18px;
}

.hero-create {
  width: 100%;
  min-height: 284px;
  border-radius: 34px;
  display: grid;
  justify-items: center;
  align-content: center;
  gap: 14px;
  color: white;
  overflow: hidden;
}

.hero-create::before {
  content: "";
  position: absolute;
  inset: 8%;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 40%;
  transform: rotate(-17deg);
  opacity: 0.35;
}

.hero-plus {
  position: relative;
  z-index: 1;
  width: 82px;
  height: 82px;
  display: grid;
  place-items: center;
  border-radius: 28px;
  color: rgba(7, 16, 24, 0.78);
  background: rgba(255, 255, 255, 0.95);
  box-shadow: 0 14px 42px rgba(0, 0, 0, 0.18);
}

.hero-title {
  position: relative;
  z-index: 1;
  font-size: 34px;
  font-weight: 900;
  letter-spacing: -0.05em;
}

.hero-subtitle {
  position: relative;
  z-index: 1;
  font-size: 17px;
  color: rgba(255, 255, 255, 0.78);
}

.home-shortcuts {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
  margin-top: 18px;
}

.shortcut-card {
  min-height: 156px;
  display: grid;
  justify-items: center;
  align-content: center;
  gap: 8px;
  color: var(--text);
  text-align: center;
}

.shortcut-card svg {
  color: var(--text);
}

.shortcut-card strong {
  font-size: 21px;
  letter-spacing: -0.03em;
}

.shortcut-card span {
  font-size: 13px;
  color: var(--muted);
}

.recent-section {
  margin-top: 34px;
}

.recent-section h2 {
  margin: 0 0 16px;
  font-size: 25px;
  letter-spacing: -0.04em;
}

.recent-task {
  width: 100%;
  min-height: 140px;
  display: grid;
  grid-template-columns: 102px 1fr 46px;
  gap: 14px;
  align-items: center;
  color: var(--text);
  text-align: left;
}

.recent-thumb {
  position: relative;
  width: 102px;
  height: 102px;
  display: grid;
  place-items: center;
  border-radius: 24px;
  color: var(--accent);
  background:
    radial-gradient(circle at 72% 18%, rgba(255, 209, 90, 0.26), transparent 25%),
    linear-gradient(145deg, rgba(255, 255, 255, 0.12), rgba(255, 255, 255, 0.035));
}

.recent-thumb small {
  position: absolute;
  left: 10px;
  bottom: 9px;
  color: white;
  font-weight: 900;
}

.recent-copy {
  display: grid;
  gap: 8px;
  min-width: 0;
}

.recent-copy strong {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 20px;
  font-weight: 800;
}

.recent-copy em {
  width: max-content;
  padding: 4px 10px;
  border-radius: 999px;
  color: var(--accent);
  background: rgba(53, 225, 192, 0.12);
  font-size: 13px;
  font-style: normal;
  font-weight: 800;
}

.recent-copy small {
  color: var(--muted);
  font-size: 12px;
}

.recent-more {
  width: 46px;
  height: 46px;
  display: grid;
  place-items: center;
  border-radius: 999px;
  color: rgba(255, 255, 255, 0.75);
  background: rgba(255, 255, 255, 0.08);
}

.empty-recent {
  display: flex;
  align-items: center;
  gap: 12px;
  color: var(--muted);
}
</style>
