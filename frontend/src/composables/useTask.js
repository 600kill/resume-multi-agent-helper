import { reactive } from 'vue'
import { getRecordDetail } from '../api'

// 任务轮询状态：currentRecordId 存 localStorage，刷新后可继续轮询
const state = reactive({
  currentRecordId: Number(localStorage.getItem('currentRecordId')) || null,
  status: null,
  polling: false,
  error: '',
  pollTimer: null,
  // 已运行时长（秒），由前端计时器维护
  elapsed: 0,
  elapsedTimer: null,
})

function setRecordId(id) {
  state.currentRecordId = id
  if (id) {
    localStorage.setItem('currentRecordId', String(id))
  } else {
    localStorage.removeItem('currentRecordId')
  }
}

function startElapsedTimer() {
  stopElapsedTimer()
  state.elapsed = 0
  state.elapsedTimer = setInterval(() => {
    state.elapsed += 1
  }, 1000)
}

function stopElapsedTimer() {
  if (state.elapsedTimer) {
    clearInterval(state.elapsedTimer)
    state.elapsedTimer = null
  }
}

function startPolling(onUpdate, intervalMs = 1500) {
  if (state.polling) return
  if (!state.currentRecordId) return
  state.polling = true
  state.error = ''
  startElapsedTimer()

  const tick = async () => {
    if (!state.currentRecordId) {
      stopPolling()
      return
    }
    try {
      const { data } = await getRecordDetail(state.currentRecordId)
      state.status = data
      onUpdate?.(data)
      // 终态停止轮询
      if (['done', 'error'].includes(data.status)) {
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
  stopElapsedTimer()
}

function reset() {
  stopPolling()
  setRecordId(null)
  state.status = null
  state.error = ''
  state.elapsed = 0
}

export function useTask() {
  return { state, setRecordId, startPolling, stopPolling, reset }
}
