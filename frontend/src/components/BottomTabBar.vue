<script setup>
import {
  IconClipboardText,
  IconMicrophone2,
  IconUserCircle,
  IconWand,
} from '@tabler/icons-vue'
import { state, navigate } from '../state/creationState.js'

const tabs = [
  { key: 'create', label: '创作', page: 'create-home', icon: IconWand },
  { key: 'tasks', label: '任务', page: 'task-list', icon: IconClipboardText },
  { key: 'voices', label: '音色', page: 'voice-library', icon: IconMicrophone2 },
  { key: 'me', label: '我的', page: 'me', icon: IconUserCircle },
]
</script>

<template>
  <nav class="bottom-bar">
    <div class="tabs-wrap">
      <button
        v-for="tab in tabs"
        :key="tab.key"
        :class="['tab', state.activeTab === tab.key && 'active']"
        type="button"
        @click="navigate(tab.page)"
      >
        <component :is="tab.icon" :size="28" stroke-width="1.8" />
        <span>{{ tab.label }}</span>
        <span v-if="state.activeTab === tab.key" class="active-line" />
      </button>
    </div>
  </nav>
</template>
