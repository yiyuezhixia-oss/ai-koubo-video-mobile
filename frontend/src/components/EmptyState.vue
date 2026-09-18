<script setup>
import { IconMoodEmpty } from '@tabler/icons-vue'

defineProps({
  text: {
    type: String,
    default: '暂无数据',
  },
})
</script>

<template>
  <div class="empty-state">
    <IconMoodEmpty :size="48" stroke-width="1.4" />
    <p>{{ text }}</p>
  </div>
</template>

<style scoped>
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 48px 0;
  color: var(--muted);
}

.empty-state p {
  margin: 0;
  font-size: 14px;
}
</style>
