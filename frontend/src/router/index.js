import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/login',
    name: 'login',
    component: () => import('../views/Login.vue'),
    meta: { guest: true },
  },
  {
    path: '/register',
    name: 'register',
    component: () => import('../views/Register.vue'),
    meta: { guest: true },
  },
  {
    path: '/',
    name: 'home',
    component: () => import('../views/HomeView.vue'),
    meta: { auth: true },
  },
  {
    path: '/history',
    name: 'history',
    component: () => import('../views/HistoryList.vue'),
    meta: { auth: true },
  },
  {
    path: '/history/:id',
    name: 'historyDetail',
    component: () => import('../views/HistoryDetail.vue'),
    meta: { auth: true },
  },
  { path: '/:pathMatch(.*)*', redirect: '/' },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// 路由守卫
router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('token')
  if (to.meta.auth && !token) {
    next({ name: 'login' })
  } else if (to.meta.guest && token) {
    next({ name: 'home' })
  } else {
    next()
  }
})

export default router
