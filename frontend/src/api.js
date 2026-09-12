import axios from 'axios'

const http = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

export function checkHealth() {
  return http.get('/health')
}

// 5 Agent 串行 + 质检可能迭代，实测一轮约 2-3 分钟，最坏多轮可达 5 分钟以上
export function analyzeResume(payload) {
  return http.post('/analyze', payload, { timeout: 600000 })
}

export function listRecords() {
  return http.get('/records')
}

export function getRecord(id) {
  return http.get(`/records/${id}`)
}

export default http