<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuth } from '../composables/useAuth'

const router = useRouter()
const { login } = useAuth()

const form = reactive({ username: '', password: '' })
const loading = ref(false)
const error = ref('')

async function onSubmit() {
  if (!form.username || !form.password) {
    error.value = '请填写用户名和密码'
    return
  }
  loading.value = true
  error.value = ''
  try {
    await login(form.username, form.password)
    router.push('/')
  } catch (e) {
    error.value = e.response?.data?.detail || '登录失败，请重试'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="auth-page">
    <div class="auth-card">
      <h2>登录</h2>
      <p class="subtitle">使用您的账号继续</p>
      <form @submit.prevent="onSubmit" class="form">
        <label class="field">
          <span>用户名</span>
          <input v-model="form.username" type="text" placeholder="输入用户名" autocomplete="username" />
        </label>
        <label class="field">
          <span>密码</span>
          <input v-model="form.password" type="password" placeholder="输入密码" autocomplete="current-password" />
        </label>
        <p v-if="error" class="error">{{ error }}</p>
        <button class="submit" :disabled="loading" type="submit">
          {{ loading ? '登录中…' : '登录' }}
        </button>
        <p class="link">
          还没有账号？<router-link to="/register">立即注册</router-link>
        </p>
      </form>
    </div>
  </div>
</template>

<style scoped>
.auth-page {
  min-height: calc(100vh - 56px);
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--paper);
}

.auth-card {
  background: var(--card);
  padding: 40px 36px;
  border-radius: 12px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.06);
  width: 100%;
  max-width: 420px;
  border: 1px solid var(--border);
}

h2 {
  font-size: 24px;
  margin-bottom: 6px;
}

.subtitle {
  color: var(--slate);
  font-size: 14px;
  margin: 0 0 28px;
}

.form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.field span {
  font-size: 13px;
  color: var(--slate);
  font-weight: 500;
}

.field input {
  padding: 10px 12px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: #fff;
  transition: border 0.15s;
}

.field input:focus {
  outline: none;
  border-color: var(--accent);
}

.submit {
  background: var(--ink);
  color: #fff;
  border: none;
  padding: 12px;
  border-radius: 8px;
  font-size: 15px;
  font-weight: 500;
  margin-top: 8px;
  transition: opacity 0.15s;
}

.submit:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.link {
  text-align: center;
  color: var(--slate);
  font-size: 13px;
  margin: 12px 0 0;
}

.link a {
  color: var(--accent);
  text-decoration: none;
  font-weight: 500;
}

.error {
  color: var(--danger);
  font-size: 13px;
  margin: 0;
  padding: 8px 10px;
  background: rgba(192, 72, 63, 0.08);
  border-radius: 6px;
}
</style>
