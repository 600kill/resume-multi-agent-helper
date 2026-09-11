import axios from 'axios'

const http = axios.create({
  baseURL: '/api',
  timeout: 120000,
})

export function checkHealth() {
  return http.get('/health')
}

export function analyzeResume(payload) {
  return http.post('/analyze', payload)
}

export function listRecords() {
  return http.get('/records')
}

export function getRecord(id) {
  return http.get(`/records/${id}`)
}

export default http