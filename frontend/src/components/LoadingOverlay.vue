<script setup>
const props = defineProps({
  text: {
    type: String,
    default: '加载中...'
  }
})
</script>

<template>
  <div class="loading-overlay">
    <div class="loading-content">
      <div class="loading-spinner">
        <div class="spinner"></div>
      </div>
      <div class="loading-text">{{ text }}</div>
    </div>
  </div>
</template>

<style scoped>
.loading-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
}

.loading-content {
  background: var(--card-strong);
  padding: 30px 40px;
  border-radius: 20px;
  border: 1px solid var(--line);
  text-align: center;
  min-width: 200px;
}

.loading-spinner {
  margin-bottom: 15px;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 3px solid rgba(255, 255, 255, 0.1);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.loading-text {
  font-size: 16px;
  font-weight: 600;
  color: var(--text);
}
</style>
