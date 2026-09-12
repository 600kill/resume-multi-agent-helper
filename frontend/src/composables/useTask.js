import { reactive } from 'vue'
import { getTaskStatus } from '../api'

// 任务轮询状态：currentRecordId 存 localStorage，刷新后可继续轮询
const state = reactive({
  currentRecordId: Number(localStorage.getItem('currentRecordId')) || null,
  status: null,
  polling: false,
  error: '',
  pollTimer: null,
})

function setRecordId(id) {
  state.currentRecordId = id
  if (id) {
    localStorage.setItem('currentRecordId', String(id))
  } else {
    localStorage.removeItem('currentRecordId')
  }
}

function startPolling(onUpdate, intervalMs = 1500) {
  if (state.polling) return
  if (!state.currentRecordId) return
  state.polling = true
  state.error = ''

  const tick = async () => {
    if (!state.currentRecordId) {
      stopPolling()
      return
    }
    try {
      const { data } = await getTaskStatus(state.currentRecordId)
      state.status = data
      onUpdate?.(data)
      // 终态停止轮询
      const terminal = ['done', 'stopped', 'error', 'iterating']
      // iterating 也停（等用户操作），done/stopped/error 终态
      if (['done', 'stopped', 'error'].includes(data.status)) {
        stopPolling()
        return
      }
      // iterating：首轮/迭代轮跑完后是 iterating，也停（等用户决定继续或停止）
      if (data.status === 'iterating' && !data.current_step) {
        stopPolling()
        return
      }
    } catch (e) {
      state.error = e.response?.data?.detail || e.message
      stopPolling()
    }
  }

  tick()
  state.pollTimer = setInterval(tick, intervalMs)
}

function stopPolling() {
  state.polling = false
  if (state.pollTimer) {
    clearInterval(state.pollTimer)
    state.pollTimer = null
  }
}

function reset() {
  stopPolling()
  setRecordId(null)
  state.status = null
  state.error = ''
}

export function useTask() {
  return { state, setRecordId, startPolling, stopPolling, reset }
}
