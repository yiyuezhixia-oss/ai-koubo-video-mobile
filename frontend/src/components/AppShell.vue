<template>
  <div class="app-stage">
    <main class="phone-shell">
      <section class="page-content">
        <div v-if="state.errorMessage" class="server-error" role="alert">
          <span>{{ state.errorMessage }}</span>
          <button type="button" aria-label="关闭错误提示" @click="state.errorMessage = ''">×</button>
        </div>
        <slot />
      </section>
      <BottomTabBar v-if="showBottomTab" />
    </main>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import BottomTabBar from './BottomTabBar.vue'
import { state } from '../state/creationState.js'

const mainPages = ['create-home', 'task-list', 'voice-library', 'me']
const showBottomTab = computed(() => mainPages.includes(state.currentPage))
</script>

<style scoped>
.server-error {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
  padding: 12px 14px;
  border: 1px solid rgba(255, 108, 108, 0.35);
  border-radius: 14px;
  color: #ffd0d0;
  background: rgba(112, 25, 25, 0.3);
  font-size: 13px;
  line-height: 1.5;
}

.server-error button {
  flex: 0 0 auto;
  color: #ffd0d0;
  background: transparent;
  font-size: 20px;
}
</style>
