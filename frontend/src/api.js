import axios from 'axios'

const http = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

// 请求拦截器：注入 JWT
http.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// 响应拦截器：401 → 清 token + 跳登录
http.interceptors.response.use(
  (resp) => resp,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      // 避免在登录页死循环跳转
      if (!location.pathname.startsWith('/login')) {
        location.href = '/login'
      }
    }
    return Promise.reject(err)
  }
)

// ---------------------------- 健康检查 ---------------------------- //
export function checkHealth() {
  return http.get('/health')
}

// ---------------------------- 认证 ---------------------------- //
export function register(payload) {
  return http.post('/auth/register', payload)
}

export function login(payload) {
  return http.post('/auth/login', payload)
}

export function getMe() {
  return http.get('/auth/me')
}

// ---------------------------- 任务（异步队列） ---------------------------- //
export function createTask(payload) {
  return http.post('/tasks', payload)
}

export function getTaskStatus(recordId) {
  return http.get(`/tasks/${recordId}`)
}

export function iterateTask(recordId) {
  return http.post(`/tasks/${recordId}/iterate`)
}

export function stopTask(recordId) {
  return http.post(`/tasks/${recordId}/stop`)
}

// ---------------------------- 历史记录 ---------------------------- //
export function listRecords() {
  return http.get('/records')
}

export function getRecordDetail(id) {
  return http.get(`/records/${id}`)
}

export default http
