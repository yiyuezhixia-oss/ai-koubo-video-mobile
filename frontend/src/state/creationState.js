import { reactive } from 'vue'

const state = reactive({
  currentPage: 'create-home',
  activeTab: 'create',
  user: {
    id: null,
    uid: '',
    nickname: '',
    point_balance: 0,
    frozen_balance: 0,
    total_consumed: 0,
    total_redeemed: 0,
  },
  currentTask: null,
  voices: [],
  tasks: [],
  loading: false,
  errorMessage: '',
  cloneReturnPage: 'voice-library',
  pendingVoice: null,
  complianceSection: 'agreement',
})

async function loadUser() {
  try {
    const { getMe } = await import('../api/mockApi.js')
    await getMe()
    state.errorMessage = ''
  } catch (error) {
    state.errorMessage = error.message || '用户信息加载失败'
  }
}

async function loadTasks() {
  try {
    const { listTasks } = await import('../api/mockApi.js')
    await listTasks()
    state.errorMessage = ''
  } catch (error) {
    state.tasks = []
    state.errorMessage = error.message || '任务加载失败'
  }
}

async function loadVoices() {
  try {
    const { listVoices } = await import('../api/mockApi.js')
    await listVoices()
    state.errorMessage = ''
  } catch (error) {
    state.voices = []
    state.errorMessage = error.message || '音色加载失败'
  }
}

function setCurrentTask(task) {
  state.currentTask = task
}

function updateCurrentTask(updates) {
  if (state.currentTask) {
    Object.assign(state.currentTask, updates)
  }
}

function navigate(page) {
  state.currentPage = page
  if (['create-home', 'script-input', 'rewrite-review', 'tts-generate', 'video-upload', 'generating', 'video-preview'].includes(page)) {
    state.activeTab = 'create'
  } else if (page === 'task-list') {
    state.activeTab = 'tasks'
  } else if (page === 'voice-library' || page === 'voice-clone') {
    state.activeTab = 'voices'
  } else if (page === 'me') {
    state.activeTab = 'me'
  }
}

function navigateToVoiceClone(returnPage = 'voice-library') {
  state.cloneReturnPage = returnPage
  state.pendingVoice = null
  navigate('voice-clone')
}

function navigateToCompliance(section) {
  state.complianceSection = section
  navigate('compliance')
}

function switchTab(tab) {
  state.activeTab = tab
  if (tab === 'create') {
    state.currentPage = 'create-home'
  } else if (tab === 'tasks') {
    state.currentPage = 'task-list'
  } else if (tab === 'voices') {
    state.currentPage = 'voice-library'
  } else if (tab === 'me') {
    state.currentPage = 'me'
  }
}

export {
  state,
  navigate,
  navigateToVoiceClone,
  navigateToCompliance,
  switchTab,
  loadUser,
  loadTasks,
  loadVoices,
  setCurrentTask,
  updateCurrentTask,
}
