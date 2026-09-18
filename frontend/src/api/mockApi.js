import { state } from '../state/creationState.js'

// Same-origin by default so deployed and LAN clients call the server they opened,
// rather than resolving 127.0.0.1 to their own computer.
const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api'
const ACCESS_TOKEN_KEY = 'zhixia_access_token'
let authPromise = null

function saveAccessToken(token) {
  localStorage.setItem(ACCESS_TOKEN_KEY, token)
  return token
}

async function createDevelopmentSession() {
  const response = await fetch(`${API_BASE}/auth/anonymous/`, {
    method: 'POST',
    headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
    body: '{}',
  })
  const payload = await response.json()
  if (!response.ok || payload.success === false || !payload.data?.access_token) {
    throw new Error(payload.message || '登录失败')
  }
  return saveAccessToken(payload.data.access_token)
}

async function ensureAccessToken() {
  const stored = localStorage.getItem(ACCESS_TOKEN_KEY)
  if (stored) return stored
  if (!authPromise) {
    authPromise = createDevelopmentSession().finally(() => {
      authPromise = null
    })
  }
  return authPromise
}

function idempotency(prefix) {
  return `${prefix}_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`
}

async function request(path, options = {}, retryAuthentication = true) {
  const accessToken = await ensureAccessToken()
  const headers = {
    Accept: 'application/json',
    Authorization: `Bearer ${accessToken}`,
    ...(options.body instanceof FormData ? {} : { 'Content-Type': 'application/json' }),
    ...(options.headers || {}),
  }
  let response
  try {
    response = await fetch(`${API_BASE}${path}`, { ...options, headers })
  } catch (cause) {
    throw new Error('无法连接服务器，请检查网络后重试', { cause })
  }
  const text = await response.text()
  let payload = {}
  try {
    payload = text ? JSON.parse(text) : {}
  } catch {
    payload = { message: text || response.statusText }
  }
  if (response.status === 401 && retryAuthentication) {
    localStorage.removeItem(ACCESS_TOKEN_KEY)
    return request(path, options, false)
  }
  if (!response.ok || payload.success === false) {
    const error = new Error(payload.message || '请求失败')
    error.fromApi = true
    error.status = response.status
    throw error
  }
  return payload.data
}

export async function loginWithWechat(code, profile = {}) {
  const response = await fetch(`${API_BASE}/auth/wechat/`, {
    method: 'POST',
    headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
    body: JSON.stringify({
      code,
      nickname: profile.nickname || '',
      avatar_url: profile.avatar_url || '',
    }),
  })
  const payload = await response.json()
  if (!response.ok || payload.success === false || !payload.data?.access_token) {
    throw new Error(payload.message || '微信登录失败')
  }
  saveAccessToken(payload.data.access_token)
  return payload.data
}

function syncUserFromAccount(account) {
  if (!account) return
  state.user.point_balance = account.balance
  state.user.frozen_balance = account.frozen_balance
  state.user.total_consumed = account.total_consumed
  state.user.total_redeemed = account.total_redeemed
}

function normalizeTask(payload) {
  const task = payload?.task || payload
  if (payload?.account) syncUserFromAccount(payload.account)
  return task
}

function normalizeVoice(payload) {
  const voice = payload?.voice || payload
  if (payload?.account) syncUserFromAccount(payload.account)
  return voice
}

export async function getMe() {
  const data = await request('/me/')
  syncUserFromAccount(data.account)
  state.user = {
    ...state.user,
    ...data.user,
    point_balance: data.account.balance,
  }
  return state.user
}

export async function redeemCode(code) {
  const data = await request('/points/redeem-code/', {
    method: 'POST',
    body: JSON.stringify({ code }),
  })
  syncUserFromAccount(data.account)
  return data.account
}

export async function getPointBalance() {
  await getMe()
  return state.user.point_balance
}

export async function getPricing({ text = '', duration_seconds = 60 } = {}) {
  return request('/pricing/', {
    method: 'POST',
    body: JSON.stringify({ text, duration_seconds }),
  })
}

export async function createTask(originalText = '', options = {}) {
  return normalizeTask(await request('/tasks/', {
    method: 'POST',
    body: JSON.stringify({
      original_text: originalText,
      source_type: options.source_type || 'douyin_link',
      source_url: options.source_url || '',
    }),
  }))
}

export async function rewriteScript(taskId, text, key = idempotency('rewrite'), requirement = '') {
  const task = normalizeTask(await request(`/tasks/${taskId}/rewrite/`, {
    method: 'POST',
    headers: { 'X-Idempotency-Key': key },
    body: JSON.stringify({ text, Requirement: requirement }),
  }))
  return {
    ...task,
    point_cost: 1,
  }
}

export async function listVoices() {
  const data = await request('/voices/?status=available')
  state.voices = data.items
  return data.items
}

export async function previewCloneVoice(fileOrName, voiceName, testText, authorization, key = idempotency('voice_preview')) {
  if (!(fileOrName instanceof File)) {
    throw new Error('请选择用于克隆的音频文件')
  }
  const body = new FormData()
  body.append('audio_file', fileOrName)
  body.append('voice_name', voiceName)
  body.append('text', testText)
  body.append('ownership_confirmed', authorization?.ownershipConfirmed ? 'true' : 'false')
  body.append('separate_consent_confirmed', authorization?.separateConsentConfirmed ? 'true' : 'false')
  return normalizeVoice(await request('/voices/clone/preview/', {
    method: 'POST',
    headers: { 'X-Idempotency-Key': key },
    body,
  }))
}

export async function createUserRightsRequest(requestType, content = '') {
  return request('/user-rights/', {
    method: 'POST',
    body: JSON.stringify({ request_type: requestType, content }),
  })
}

export async function confirmVoice(voiceId, key = idempotency('voice_confirm')) {
  const voice = normalizeVoice(await request(`/voices/${voiceId}/confirm/`, {
    method: 'POST',
    headers: { 'X-Idempotency-Key': key },
  }))
  await listVoices()
  return voice
}

export async function discardVoice(voiceId) {
  return normalizeVoice(await request(`/voices/${voiceId}/discard/`, { method: 'POST' }))
}

export async function cloneVoice(fileName, voiceName, testText, authorization, key = idempotency('voice_clone')) {
  const preview = await previewCloneVoice(fileName, voiceName, testText, authorization, `${key}:preview`)
  return confirmVoice(preview.id, `${key}:confirm`)
}

export async function generateTts(taskId, voiceId, text, options = {}, key = idempotency('tts')) {
  const data = await request(`/tasks/${taskId}/tts/`, {
    method: 'POST',
    headers: { 'X-Idempotency-Key': key },
    body: JSON.stringify({
      voice_id: voiceId,
      text,
      pitch: options.pitch ?? 0,
      speed: options.speed ?? 1,
      volume: options.volume ?? 1,
      emotion: options.emotion || '',
    }),
  })
  const task = normalizeTask(data)
  return {
    ...task,
    tts_audio_url: task.tts_audio_url,
    point_cost: data.points || 0,
  }
}

export async function uploadVideo(taskId, fileOrName, duration = 60) {
  if (!(fileOrName instanceof File)) {
    throw new Error('请选择要上传的视频文件')
  }
  const body = new FormData()
  body.append('file', fileOrName)
  body.append('task_id', taskId)
  body.append('file_type', 'source_video')
  body.append('duration', duration)
  const data = await request('/media/upload/', {
    method: 'POST',
    body,
  })
  return {
    ...data.media,
    file_name: data.media.file_name || fileOrName.name,
    task: data.task,
  }
}

export async function generateVideo(taskId, key = idempotency('digital_human')) {
  const data = await request(`/tasks/${taskId}/digital-human/`, {
    method: 'POST',
    headers: { 'X-Idempotency-Key': key },
  })
  const task = normalizeTask(data)
  return {
    ...task,
    output_video_url: task.output_video_url,
    point_cost: data.job?.cost_points || 0,
  }
}

export async function syncVideoTask(taskId, key = idempotency('digital_human_sync')) {
  const data = await request(`/tasks/${taskId}/sync/`, {
    method: 'POST',
    headers: { 'X-Idempotency-Key': key },
  })
  return {
    task: normalizeTask(data),
    job: data.job || null,
  }
}

export async function listTasks() {
  const data = await request('/tasks/')
  state.tasks = data.items
  return data.items
}

export async function getTask(taskId) {
  return normalizeTask(await request(`/tasks/${taskId}/`))
}
