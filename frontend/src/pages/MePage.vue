<script setup>
import { onMounted, ref } from 'vue'
import { IconChevronRight, IconCoins, IconCopy, IconGift, IconUserCircle } from '@tabler/icons-vue'
import { getMe, redeemCode } from '../api/mockApi.js'
import { navigateToCompliance, state } from '../state/creationState.js'

const code = ref('')
const loading = ref(false)
const message = ref('')
const error = ref('')

onMounted(() => {
  getMe()
})

async function submitCode() {
  if (!code.value.trim()) {
    error.value = '请输入兑换码'
    return
  }
  loading.value = true
  error.value = ''
  message.value = ''
  try {
    const account = await redeemCode(code.value.trim())
    message.value = `兑换成功，当前余额 ${account.balance} 积分`
    code.value = ''
  } catch (e) {
    error.value = e.message || '兑换失败，请检查兑换码'
  } finally {
    loading.value = false
  }
}

function copyUid() {
  navigator.clipboard?.writeText(state.user.uid || '')
  message.value = 'UID 已复制'
}
</script>

<template>
  <div class="me-page">
    <h1 class="page-title">我的</h1>

    <section class="profile-card gradient-panel">
      <div class="avatar">
        <IconUserCircle :size="62" stroke-width="1.5" />
      </div>
      <div class="profile-copy">
        <strong>{{ state.user.nickname || '一月知夏' }}</strong>
        <button type="button" class="uid-row" @click="copyUid">
          UID：{{ state.user.uid || state.user.id || '-' }}
          <IconCopy :size="16" stroke-width="2" />
        </button>
      </div>
    </section>

    <section class="point-card card">
      <div>
        <span class="muted text-sm">当前积分</span>
        <strong>{{ state.user.point_balance ?? 0 }}</strong>
        <small>冻结 {{ state.user.frozen_balance ?? 0 }} · 已消费 {{ state.user.total_consumed ?? 0 }}</small>
      </div>
      <span class="coin-mark">
        <IconCoins :size="34" stroke-width="1.8" />
      </span>
    </section>

    <section class="redeem-card card">
      <div class="section-title">
        <IconGift :size="24" stroke-width="1.8" />
        <strong>兑换码充值</strong>
      </div>
      <p>当前只支持兑换码充值，后续真实运营时可在 Django 后台生成和管理兑换码。</p>
      <div class="redeem-row">
        <input v-model="code" type="text" placeholder="输入兑换码" />
        <button type="button" :disabled="loading" @click="submitCode">
          {{ loading ? '兑换中' : '兑换' }}
        </button>
      </div>
      <p v-if="message" class="success-text">{{ message }}</p>
      <p v-if="error" class="error-text">{{ error }}</p>
    </section>

    <section class="card quick-list">
      <button type="button" @click="navigateToCompliance('agreement')">
        <span>用户协议</span>
        <IconChevronRight :size="20" stroke-width="2" />
      </button>
      <button type="button" @click="navigateToCompliance('privacy')">
        <span>隐私政策</span>
        <IconChevronRight :size="20" stroke-width="2" />
      </button>
      <button type="button" @click="navigateToCompliance('ai')">
        <span>AI 服务说明</span>
        <IconChevronRight :size="20" stroke-width="2" />
      </button>
      <button type="button" @click="navigateToCompliance('complaint')">
        <span>投诉举报</span>
        <IconChevronRight :size="20" stroke-width="2" />
      </button>
      <button type="button" @click="navigateToCompliance('data_export')">
        <span>导出个人数据</span>
        <IconChevronRight :size="20" stroke-width="2" />
      </button>
      <button type="button" @click="navigateToCompliance('data_delete')">
        <span>删除个人数据</span>
        <IconChevronRight :size="20" stroke-width="2" />
      </button>
      <button class="danger-row" type="button" @click="navigateToCompliance('account_delete')">
        <span>注销账号</span>
        <IconChevronRight :size="20" stroke-width="2" />
      </button>
    </section>
  </div>
</template>

<style scoped>
.me-page {
  padding-top: 4px;
}

.profile-card {
  position: relative;
  min-height: 154px;
  display: flex;
  align-items: center;
  gap: 18px;
  padding: 24px;
  border-radius: 34px;
  overflow: hidden;
}

.avatar {
  width: 76px;
  height: 76px;
  display: grid;
  place-items: center;
  flex: 0 0 auto;
  border-radius: 28px;
  color: rgba(6, 16, 24, 0.78);
  background: rgba(255, 255, 255, 0.92);
}

.profile-copy {
  display: grid;
  gap: 8px;
}

.profile-copy strong {
  color: #071018;
  font-size: 28px;
  font-weight: 900;
  letter-spacing: -0.04em;
}

.uid-row {
  width: fit-content;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 7px 12px;
  border-radius: 999px;
  color: rgba(7, 16, 24, 0.74);
  background: rgba(255, 255, 255, 0.45);
  font-size: 13px;
  font-weight: 800;
}

.point-card {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 18px;
  padding: 24px;
}

.point-card strong {
  display: block;
  margin-top: 4px;
  font-size: 46px;
  line-height: 1;
  letter-spacing: -0.07em;
}

.point-card small {
  display: block;
  margin-top: 8px;
  color: var(--muted);
}

.coin-mark {
  width: 66px;
  height: 66px;
  display: grid;
  place-items: center;
  border-radius: 22px;
  color: var(--accent-2);
  background: rgba(255, 209, 90, 0.11);
}

.redeem-card {
  margin-top: 18px;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--accent);
  font-size: 20px;
}

.redeem-card p {
  margin: 12px 0 0;
  color: var(--muted);
  line-height: 1.55;
}

.redeem-row {
  display: grid;
  grid-template-columns: 1fr 86px;
  gap: 10px;
  margin-top: 16px;
}

.redeem-row input {
  min-width: 0;
  height: 52px;
  padding: 0 16px;
  outline: none;
  border: 1px solid var(--line);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.07);
}

.redeem-row button {
  border-radius: 18px;
  color: #061018;
  background: linear-gradient(100deg, var(--accent), var(--accent-2));
  font-weight: 900;
}

.success-text {
  color: var(--accent) !important;
  font-weight: 800;
}

.quick-list {
  display: grid;
  gap: 2px;
  margin-top: 18px;
}

.quick-list button {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 6px 12px;
  align-items: center;
  padding: 15px 2px;
  text-align: left;
  background: transparent;
  border-bottom: 1px solid var(--line);
}

.quick-list button:last-child {
  border-bottom: 0;
}

.quick-list span {
  font-size: 17px;
  font-weight: 900;
}

.quick-list em {
  grid-column: 1 / 2;
  color: var(--muted);
  font-size: 13px;
  font-style: normal;
}

.quick-list .danger-row span {
  color: var(--danger);
}
</style>
