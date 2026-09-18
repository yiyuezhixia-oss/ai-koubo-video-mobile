<script setup>
import { state } from './state/creationState.js'
import AppShell from './components/AppShell.vue'
import CreateHome from './pages/CreateHome.vue'
import ScriptInput from './pages/ScriptInput.vue'
import RewriteReview from './pages/RewriteReview.vue'
import VoiceLibrary from './pages/VoiceLibrary.vue'
import VoiceClone from './pages/VoiceClone.vue'
import TtsGenerate from './pages/TtsGenerate.vue'
import VideoUpload from './pages/VideoUpload.vue'
import Generating from './pages/Generating.vue'
import VideoPreview from './pages/VideoPreview.vue'
import TaskList from './pages/TaskList.vue'
import MePage from './pages/MePage.vue'
import ComplianceCenter from './pages/ComplianceCenter.vue'

// 页面 key → 组件映射
const pageMap = {
  'create-home': CreateHome,
  'script-input': ScriptInput,
  'rewrite-review': RewriteReview,
  'voice-library': VoiceLibrary,
  'voice-clone': VoiceClone,
  'tts-generate': TtsGenerate,
  'video-upload': VideoUpload,
  'generating': Generating,
  'video-preview': VideoPreview,
  'task-list': TaskList,
  me: MePage,
  compliance: ComplianceCenter,
}
</script>

<template>
  <AppShell>
    <component :is="pageMap[state.currentPage]" v-if="pageMap[state.currentPage]" />
    <div v-else class="card" style="text-align: center; padding: 48px;">
      <p class="muted">页面未找到</p>
    </div>
  </AppShell>
</template>
