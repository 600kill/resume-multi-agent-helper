<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { listRecords } from '../api'

const router = useRouter()
const records = ref([])
const loading = ref(false)
const error = ref('')

async function load() {
  loading.value = true
  error.value = ''
  try {
    const { data } = await listRecords()
    records.value = data
  } catch (e) {
    error.value = e.response?.data?.detail || '加载失败'
  } finally {
    loading.value = false
  }
}

function viewDetail(id) {
  router.push(`/history/${id}`)
}

function statusLabel(s) {
  return { pending: '等待', running: '执行中', iterating: '可迭代', done: '已完成', stopped: '已停止', error: '错误' }[s] || s
}

function statusClass(s) {
  return `st-${s}`
}

onMounted(load)
</script>

<template>
  <div class="card">
    <div class="head">
      <h2>历史记录</h2>
      <button class="btn-refresh" @click="load" :disabled="loading">刷新</button>
    </div>
    <p v-if="error" class="error">{{ error }}</p>
    <p v-else-if="!loading && records.length === 0" class="empty">
      暂无记录，<router-link to="/">去创建一个任务</router-link>
    </p>
    <table v-else class="table">
      <thead>
        <tr>
          <th>时间</th>
          <th>目标岗位</th>
          <th>方式</th>
          <th>总分</th>
          <th>轮次</th>
          <th>状态</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="r in records" :key="r.id">
          <td>{{ r.created_at?.slice(0, 19).replace('T', ' ') }}</td>
          <td>{{ r.target_position || '—' }}</td>
          <td>
            <span class="mode-mini" :class="r.mode === 'compare' ? 'mc-compare' : 'mc-optimize'">
              {{ r.mode === 'compare' ? '前后对比' : '优化测评' }}
            </span>
          </td>
          <td>{{ r.overall_score != null ? r.overall_score : '—' }}</td>
          <td>{{ r.current_round }}/3</td>
          <td><span class="badge" :class="statusClass(r.status)">{{ statusLabel(r.status) }}</span></td>
          <td><button class="btn-view" @click="viewDetail(r.id)">查看</button></td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped>
.card {
  background: var(--card); border-radius: 12px; border: 1px solid var(--border);
  padding: 28px; box-shadow: 0 1px 4px rgba(0, 0, 0, 0.04);
}
.head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px; }
h2 { font-size: 20px; }
.btn-refresh {
  background: #fff; border: 1px solid var(--border); color: var(--slate);
  padding: 6px 14px; border-radius: 6px; font-size: 13px;
}
.btn-refresh:disabled { opacity: 0.5; }

.table { width: 100%; border-collapse: collapse; font-size: 13px; }
.table th {
  text-align: left; padding: 10px 12px; color: var(--slate); font-weight: 500;
  border-bottom: 1px solid var(--border); background: var(--paper);
}
.table td { padding: 10px 12px; border-bottom: 1px solid var(--border); }
.table tr:hover td { background: var(--paper); }

.badge {
  display: inline-block; padding: 2px 10px; border-radius: 12px;
  font-size: 12px; font-weight: 500;
}
.st-pending, .st-running { background: rgba(91, 107, 124, 0.12); color: var(--slate); }
.st-iterating { background: rgba(217, 119, 87, 0.12); color: var(--accent); }
.st-done { background: rgba(47, 125, 90, 0.12); color: var(--success); }
.st-stopped { background: rgba(192, 72, 63, 0.12); color: var(--danger); }
.st-error { background: rgba(192, 72, 63, 0.12); color: var(--danger); }

.btn-view {
  background: var(--ink); color: #fff; border: none; padding: 4px 12px;
  border-radius: 6px; font-size: 12px;
}

.mode-mini {
  display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 12px; white-space: nowrap;
}
.mc-optimize { background: rgba(91, 107, 124, 0.12); color: var(--slate); }
.mc-compare { background: rgba(217, 119, 87, 0.12); color: var(--accent); }

.empty { color: var(--slate); font-size: 14px; padding: 40px 0; text-align: center; }
.empty a { color: var(--accent); }
.error {
  color: var(--danger); font-size: 13px; padding: 8px 12px;
  background: rgba(192, 72, 63, 0.08); border-radius: 6px;
}
</style>
