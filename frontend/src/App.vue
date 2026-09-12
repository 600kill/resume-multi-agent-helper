<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuth } from './composables/useAuth'

const route = useRoute()
const router = useRouter()
const { state, logout } = useAuth()

const isAuthPage = computed(() => ['/login', '/register'].includes(route.path))
const isLoggedIn = computed(() => !!state.token)

function onLogout() {
  logout()
  router.push('/login')
}
</script>

<template>
  <div class="app-shell">
    <header v-if="!isAuthPage" class="topbar">
      <div class="brand" @click="router.push('/')">
        <span class="logo">cv</span>
        <div>
          <h1>简历多智能体优化助手</h1>
          <p class="tagline">五个 AI 顾问，为你的简历把好每一关</p>
        </div>
      </div>
      <nav class="nav">
        <router-link to="/" class="nav-item">新建任务</router-link>
        <router-link to="/history" class="nav-item">历史记录</router-link>
        <div v-if="isLoggedIn" class="user-info">
          <span class="username">{{ state.user?.username }}</span>
          <button class="btn-text" @click="onLogout">退出</button>
        </div>
      </nav>
    </header>

    <main class="main-content">
      <router-view />
    </main>
  </div>
</template>

<style scoped>
.app-shell {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.topbar {
  background: var(--card);
  border-bottom: 1px solid var(--border);
  padding: 14px 32px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
}

.brand {
  display: flex;
  align-items: center;
  gap: 12px;
  cursor: pointer;
}

.logo {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border-radius: 10px;
  background: var(--ink);
  color: #fff;
  font-weight: 700;
  font-size: 16px;
}

.brand h1 {
  font-size: 17px;
  font-weight: 600;
  margin: 0;
}

.tagline {
  font-size: 12px;
  color: var(--slate);
  margin: 0;
}

.nav {
  display: flex;
  align-items: center;
  gap: 24px;
}

.nav-item {
  color: var(--slate);
  text-decoration: none;
  font-size: 14px;
  font-weight: 500;
  padding: 6px 4px;
  border-bottom: 2px solid transparent;
}

.nav-item.router-link-exact-active {
  color: var(--ink);
  border-bottom-color: var(--accent);
}

.user-info {
  display: flex;
  align-items: center;
  gap: 10px;
  padding-left: 16px;
  border-left: 1px solid var(--border);
}

.username {
  color: var(--ink);
  font-size: 14px;
  font-weight: 500;
}

.btn-text {
  background: none;
  border: 1px solid var(--border);
  color: var(--slate);
  padding: 4px 12px;
  border-radius: 6px;
  font-size: 13px;
}

.btn-text:hover {
  color: var(--danger);
  border-color: var(--danger);
}

.main-content {
  flex: 1;
  max-width: 1240px;
  width: 100%;
  margin: 0 auto;
  padding: 28px 32px;
}
</style>
