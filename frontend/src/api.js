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

// ---------------------------- 分析任务（异步） ---------------------------- //
export function analyze(payload) {
  return http.post('/analyze', payload)
}

// 兼容旧调用名
export const createTask = analyze

// 轮询任务详情（含步骤进度 + 迭代结果）
export function getRecordDetail(id) {
  return http.get(`/records/${id}`)
}

// 兼容旧调用名
export const getTaskStatus = getRecordDetail

// ---------------------------- 历史记录 ---------------------------- //
export function listRecords() {
  return http.get('/records')
}

export default http
