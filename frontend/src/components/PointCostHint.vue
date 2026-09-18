<script setup>
import { IconCoin } from '@tabler/icons-vue'

defineProps({
  cost: {
    type: Number,
    required: true,
  },
  label: {
    type: String,
    default: '预计消耗',
  },
})
</script>

<template>
  <div class="point-hint">
    <IconCoin :size="16" stroke-width="2" />
    <span>{{ label }} {{ cost }} 积分</span>
  </div>
</template>
