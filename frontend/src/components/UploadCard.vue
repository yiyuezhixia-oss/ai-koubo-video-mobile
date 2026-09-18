<script setup>
import { ref } from 'vue'
import {
  IconCloudUpload,
  IconFile,
  IconX,
} from '@tabler/icons-vue'

const props = defineProps({
  // 上传类型：audio / video
  type: {
    type: String,
    default: 'video',
  },
  // 已选文件名
  modelValue: {
    type: String,
    default: '',
  },
  // 格式提示
  acceptHint: {
    type: String,
    default: '',
  },
  status: {
    type: String,
    default: 'selected',
  },
})

const emit = defineEmits(['update:modelValue', 'file-selected'])

const inputRef = ref(null)

const defaultHint = props.type === 'audio'
  ? '支持 WAV / MP3 / M4A，建议 10 秒以上'
  : '仅支持 MP4，最大 500MB，建议 2K / 25 帧'

const hint = props.acceptHint || defaultHint

function triggerSelect() {
  inputRef.value?.click()
}

function onFileChange(e) {
  const file = e.target.files[0]
  if (file) {
    emit('update:modelValue', file.name)
    emit('file-selected', file)
  }
}

function clearFile() {
  emit('update:modelValue', '')
  emit('file-selected', null)
  if (inputRef.value) {
    inputRef.value.value = ''
  }
}
</script>

<template>
  <div>
    <input
      ref="inputRef"
      type="file"
      :accept="type === 'audio' ? 'audio/*' : '.mp4,video/mp4'"
      style="display: none;"
      @change="onFileChange"
    />

    <!-- 未选择文件时显示上传区 -->
    <div
      v-if="!modelValue"
      class="upload-zone"
      @click="triggerSelect"
    >
      <IconCloudUpload :size="36" stroke-width="1.6" />
      <span>点击上传{{ type === 'audio' ? '音频' : '视频' }}文件</span>
      <span class="text-xs muted">{{ hint }}</span>
    </div>

    <!-- 已选择文件时显示文件信息 -->
    <div v-else class="card-strong flex-between">
      <div class="flex-row" style="gap: 12px; min-width: 0;">
        <span class="file-icon">
          <IconFile :size="22" stroke-width="1.8" />
        </span>
        <div style="min-width: 0;">
          <strong style="font-size: 14px; display: block; overflow: hidden; white-space: nowrap; text-overflow: ellipsis;">{{ modelValue }}</strong>
          <span class="text-xs muted">{{ status === 'uploading' ? '上传中…' : status === 'uploaded' ? '上传成功' : '已选择，等待上传' }}</span>
        </div>
      </div>
      <button
        class="back-btn"
        style="width: 32px; height: 32px;"
        type="button"
        @click="clearFile"
      >
        <IconX :size="18" stroke-width="2" />
      </button>
    </div>
  </div>
</template>

<style scoped>
.file-icon {
  width: 40px;
  height: 40px;
  display: grid;
  place-items: center;
  border-radius: 10px;
  background: rgba(103, 232, 201, 0.12);
  color: var(--accent);
  flex-shrink: 0;
}
</style>
