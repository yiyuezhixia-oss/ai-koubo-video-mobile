<script setup>
import { computed, onMounted, ref } from 'vue'
import EmptyState from '../components/EmptyState.vue'
import TaskCard from '../components/TaskCard.vue'
import { loadTasks, state } from '../state/creationState.js'

const activeFilter = ref('all')

const filters = [
  { key: 'all', label: '全部' },
  { key: 'running', label: '生成中' },
  { key: 'completed', label: '已完成' },
  { key: 'failed', label: '失败' },
]

const filteredTasks = computed(() => {
  if (activeFilter.value === 'all') return state.tasks
  if (activeFilter.value === 'running') {
    return state.tasks.filter((task) => task.status !== 'completed' && task.status !== 'failed')
  }
  return state.tasks.filter((task) => task.status === activeFilter.value)
})

onMounted(() => {
  loadTasks()
})
</script>

<template>
  <div>
    <h1 class="page-title">任务记录</h1>

    <div class="task-filter">
      <button
        v-for="filter in filters"
        :key="filter.key"
        :class="activeFilter === filter.key && 'active'"
        type="button"
        @click="activeFilter = filter.key"
      >
        {{ filter.label }}
      </button>
    </div>

    <div v-if="filteredTasks.length" class="task-list">
      <TaskCard
        v-for="task in filteredTasks"
        :key="task.id"
        :task="task"
      />
    </div>
    <EmptyState v-else text="这里暂时没有任务" />
  </div>
</template>

<style scoped>
.task-filter {
  height: 64px;
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 4px;
  padding: 5px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.065);
  border: 1px solid var(--line);
  margin-bottom: 22px;
}

.task-filter button {
  border-radius: 999px;
  background: transparent;
  color: var(--muted);
  font-size: 17px;
  font-weight: 800;
}

.task-filter button.active {
  color: white;
  background: linear-gradient(100deg, var(--accent), #86d99b 48%, var(--accent-2));
}

.task-list {
  width: 100%;
  min-width: 0;
  display: grid;
  gap: 14px;
  overflow: hidden;
}
</style>
