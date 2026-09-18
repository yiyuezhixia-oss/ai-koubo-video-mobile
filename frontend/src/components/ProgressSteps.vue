<script setup>
import { computed } from 'vue'

const props = defineProps({
  // 当前步骤索引 (0-based)
  current: {
    type: Number,
    required: true,
  },
  // 步骤标签列表
  steps: {
    type: Array,
    default: () => ['文案', '改写', '音色', '配音', '视频', '成片'],
  },
})

const items = computed(() =>
  props.steps.map((label, index) => ({
    label,
    index,
    state: index < props.current ? 'done' : index === props.current ? 'current' : '',
  })),
)
</script>

<template>
  <div class="steps">
    <div
      v-for="item in items"
      :key="item.index"
      class="step-item"
      :class="item.state"
    >
      <span class="step-dot">{{ item.index + 1 }}</span>
      <span class="step-label">{{ item.label }}</span>
    </div>
  </div>
</template>
