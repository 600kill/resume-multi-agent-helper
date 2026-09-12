import { reactive } from 'vue'
import { login as apiLogin, register as apiRegister, getMe } from '../api'

const state = reactive({
  token: localStorage.getItem('token') || '',
  user: JSON.parse(localStorage.getItem('user') || 'null'),
})

function setAuth(token, user) {
  state.token = token
  state.user = user
  localStorage.setItem('token', token)
  localStorage.setItem('user', JSON.stringify(user))
}

function clearAuth() {
  state.token = ''
  state.user = null
  localStorage.removeItem('token')
  localStorage.removeItem('user')
}

async function login(username, password) {
  const { data } = await apiLogin({ username, password })
  setAuth(data.token, data.user)
  return data
}

async function register(username, email, password) {
  const { data } = await apiRegister({ username, email, password })
  setAuth(data.token, data.user)
  return data
}

async function fetchMe() {
  if (!state.token) return null
  try {
    const { data } = await getMe()
    state.user = data
    localStorage.setItem('user', JSON.stringify(data))
    return data
  } catch {
    clearAuth()
    return null
  }
}

function logout() {
  clearAuth()
}

export function useAuth() {
  return { state, login, register, fetchMe, logout }
}
