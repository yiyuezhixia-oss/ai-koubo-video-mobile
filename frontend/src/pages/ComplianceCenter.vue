<script setup>
import { computed, ref } from 'vue'
import { IconChevronLeft, IconSend } from '@tabler/icons-vue'
import { createUserRightsRequest } from '../api/mockApi.js'
import { navigate, state } from '../state/creationState.js'

const content = ref('')
const loading = ref(false)
const message = ref('')
const error = ref('')

const documents = {
  agreement: {
    title: '用户协议',
    sections: [
      ['服务范围', '本产品提供文案处理、文本转语音、声音克隆和数字人口型合成工具。生成结果仅供用户在合法授权范围内使用。'],
      ['禁止行为', '不得制作违法信息、虚假新闻、诈骗内容，不得冒充他人，不得未经授权处理他人的声音、肖像、视频或其他个人信息。'],
      ['费用与任务', '积分消耗以提交前页面展示为准。第三方服务失败时按产品规则退款；已经成功产生第三方成本的任务不支持无理由撤销。'],
      ['账号责任', '用户应妥善保管账号并对其提交内容负责。发现侵权、冒用或异常调用时，平台可以暂停相关能力并配合核查。'],
    ],
  },
  privacy: {
    title: '隐私政策',
    sections: [
      ['处理的信息', '我们处理账号 UID、任务文案、上传的音频和视频、生成结果、积分记录、设备与接口日志。声纹及可识别人脸属于敏感个人信息。'],
      ['处理目的', '上述信息仅用于登录、完成用户主动发起的生成任务、计费、故障排查、安全审计和处理投诉。'],
      ['第三方处理', '完成任务时，必要数据会发送给已接入的文案、TTS、声音克隆和数字人服务商。正式运营前将在此公示服务商名称、隐私政策及数据处理范围。'],
      ['保存与删除', '原始媒体仅保存完成任务所必需的期限。用户可申请导出或删除个人数据，也可以提交账号注销申请；法律要求留存的计费和安全日志除外。'],
      ['用户权利', '用户可以查询、更正、复制、删除个人信息，撤回非必要授权，并通过权益中心投诉或申请注销账号。'],
    ],
  },
  ai: {
    title: 'AI 服务说明',
    sections: [
      ['结果性质', '文案、音频和视频由人工智能生成或合成，可能存在错误。发布前必须由用户人工审核，不应将结果作为专业或事实判断的唯一依据。'],
      ['生成标识', '产品会在生成结果及展示界面保留 AI 生成提示，并按适用规则写入必要的文件标识。用户不得删除、篡改或隐匿法定标识。'],
      ['声音与肖像', '声音克隆和数字人口型处理仅限本人素材或已获得充分授权的素材。发生权利争议时，平台可以冻结音色和任务并要求补充证明。'],
      ['模型公示', '正式运营前将在此公示实际使用的模型、算法备案号或应用登记信息；测试环境中的供应商和模型可能调整。'],
    ],
  },
}

const requestTypes = {
  complaint: { title: '投诉举报', hint: '请说明涉及的任务、音色、侵权内容或其他问题。' },
  account_delete: { title: '注销账号', hint: '提交后账号将进入人工核验流程。处理前请确认没有进行中的任务。' },
  data_export: { title: '导出个人数据', hint: '我们会核验身份并提供可导出的账号、任务和积分数据。' },
  data_delete: { title: '删除个人数据', hint: '请说明希望删除的数据范围；依法必须保存的记录不会提前删除。' },
}

const document = computed(() => documents[state.complianceSection])
const requestInfo = computed(() => requestTypes[state.complianceSection])

async function submitRequest() {
  if (state.complianceSection === 'complaint' && !content.value.trim()) {
    error.value = '请填写投诉内容'
    return
  }
  loading.value = true
  error.value = ''
  message.value = ''
  try {
    const result = await createUserRightsRequest(state.complianceSection, content.value.trim())
    message.value = `申请已提交，受理编号：${result.request.id}`
    content.value = ''
  } catch (e) {
    error.value = e.message || '提交失败，请稍后重试'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div>
    <header class="page-header">
      <button class="back-btn" type="button" aria-label="返回我的" @click="navigate('me')">
        <IconChevronLeft :size="32" stroke-width="2" />
      </button>
      <h1>{{ document?.title || requestInfo?.title || '用户权益' }}</h1>
      <span />
    </header>

    <template v-if="document">
      <p class="updated">当前版本：2026-07-14</p>
      <section v-for="section in document.sections" :key="section[0]" class="document-card card">
        <h2>{{ section[0] }}</h2>
        <p>{{ section[1] }}</p>
      </section>
    </template>

    <section v-else-if="requestInfo" class="request-card card">
      <h2>{{ requestInfo.title }}</h2>
      <p>{{ requestInfo.hint }}</p>
      <textarea v-model="content" maxlength="2000" rows="8" placeholder="补充说明（最多 2000 字）" />
      <small>{{ content.length }}/2000</small>
      <p v-if="message" class="success-text">{{ message }}</p>
      <p v-if="error" class="error-text">{{ error }}</p>
      <button class="action-btn primary" type="button" :disabled="loading" @click="submitRequest">
        <IconSend :size="20" stroke-width="2" />
        {{ loading ? '提交中...' : '确认提交' }}
      </button>
    </section>
  </div>
</template>

<style scoped>
.updated {
  margin: -12px 0 16px;
  color: var(--muted);
  text-align: center;
  font-size: 13px;
}

.document-card + .document-card {
  margin-top: 14px;
}

.document-card h2,
.request-card h2 {
  margin: 0 0 10px;
  font-size: 19px;
}

.document-card p,
.request-card p {
  margin: 0;
  color: var(--muted-strong);
  line-height: 1.75;
}

.request-card {
  display: grid;
  gap: 14px;
}

.request-card textarea {
  width: 100%;
  padding: 16px;
  border: 1px solid var(--line);
  border-radius: 20px;
  outline: none;
  resize: vertical;
  background: rgba(255, 255, 255, 0.06);
  line-height: 1.6;
}

.request-card small {
  justify-self: end;
  color: var(--muted);
}

.success-text {
  color: var(--accent) !important;
  font-weight: 800;
}
</style>
