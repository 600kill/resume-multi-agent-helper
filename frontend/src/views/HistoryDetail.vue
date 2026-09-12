<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getRecordDetail } from '../api'

const route = useRoute()
const router = useRouter()
const record = ref(null)
const loading = ref(false)
const error = ref('')
const selectedRound = ref(1)

async function load() {
  loading.value = true
  error.value = ''
  try {
    const { data } = await getRecordDetail(route.params.id)
    record.value = data
    if (data.iterations.length > 0) {
      selectedRound.value = data.iterations[data.iterations.length - 1].round_number
    }
  } catch (e) {
    error.value = e.response?.data?.detail || '加载失败'
  } finally {
    loading.value = false
  }
}

const currentIteration = computed(() => {
  if (!record.value) return null
  return record.value.iterations.find((it) => it.round_number === selectedRound.value) || null
})

const qcScores = computed(() => {
  const s = currentIteration.value?.final_qc?.scores || {}
  return [
    { label: '岗位匹配度', key: 'match_score' },
    { label: '关键词覆盖', key: 'keyword_score' },
    { label: '成果表达力', key: 'impact_score' },
    { label: '结构清晰度', key: 'clarity_score' },
    { label: '真实性', key: 'authenticity_score' },
  ].map(({ label, key }) => ({ label, value: Math.max(0, Math.min(100, Number(s[key]) || 0)) }))
})

onMounted(load)
</script>

<template>
  <div class="detail" v-if="record">
    <div class="card">
      <div class="head">
        <h2>任务详情 #{{ record.id }}</h2>
        <button class="btn-back" @click="router.push('/history')">返回列表</button>
      </div>
      <div class="status-line">
        <span class="badge">状态：{{ record.status }}</span>
        <span class="round">迭代轮次：{{ record.current_round }}/3</span>
        <span class="time">{{ record.created_at?.slice(0, 19).replace('T', ' ') }}</span>
      </div>
    </div>

    <!-- 原始输入 -->
    <div class="card">
      <h3>原始输入</h3>
      <div class="kv"><b>目标岗位：</b><span>{{ record.target_position || '—' }}</span></div>
      <div class="kv"><b>简历原文：</b><pre class="raw">{{ record.resume_text }}</pre></div>
      <div v-if="record.jd_text" class="kv"><b>JD：</b><pre class="raw">{{ record.jd_text }}</pre></div>
      <div v-if="record.user_notes" class="kv"><b>补充建议：</b><span>{{ record.user_notes }}</span></div>
    </div>

    <!-- 迭代版本切换 -->
    <div class="card">
      <div class="head">
        <h3>迭代版本</h3>
        <select v-model="selectedRound" class="round-select" v-if="record.iterations.length">
          <option v-for="it in record.iterations" :key="it.round_number" :value="it.round_number">
            第 {{ it.round_number }} 轮{{ it.qc_passed ? '（合格）' : '' }}
          </option>
        </select>
      </div>

      <div v-if="currentIteration" class="iteration">
        <!-- HR 评分 -->
        <div class="qc-block">
          <h4>HR 质检评分</h4>
          <div class="scores">
            <div v-for="s in qcScores" :key="s.label" class="score">
              <div class="score-head"><span>{{ s.label }}</span><b>{{ s.value }}</b></div>
              <div class="bar"><span :style="{ width: s.value + '%' }"></span></div>
            </div>
          </div>
          <p v-if="currentIteration.final_qc?.comments" class="comment">
            {{ currentIteration.final_qc.comments }}
          </p>
          <p v-if="currentIteration.fix_instructions?.length" class="fix-list">
            <b>修改意见：</b>
            <span v-for="(it, i) in currentIteration.fix_instructions" :key="i" class="fix-item">{{ it }}</span>
          </p>
        </div>

        <!-- 优化建议 -->
        <div v-if="currentIteration.optimization_advice" class="block">
          <h4>优化建议</h4>
          <p class="overall">{{ currentIteration.optimization_advice.overall_advice }}</p>
        </div>

        <!-- 改写后简历 -->
        <div v-if="currentIteration.rewritten_resume" class="block">
          <h4>优化后简历</h4>
          <pre class="rewritten">{{ currentIteration.rewritten_resume }}</pre>
        </div>
      </div>
      <p v-else class="empty">该轮次无数据</p>
    </div>
  </div>
  <div v-else class="card">
    <p v-if="error" class="error">{{ error }}</p>
    <p v-else class="empty">加载中…</p>
  </div>
</template>

<style scoped>
.detail { display: flex; flex-direction: column; gap: 16px; }
.card {
  background: var(--card); border-radius: 12px; border: 1px solid var(--border);
  padding: 24px; box-shadow: 0 1px 4px rgba(0, 0, 0, 0.04);
}
.head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; }
h2 { font-size: 20px; }
h3 { font-size: 17px; }
h4 { font-size: 15px; margin-bottom: 12px; }

.btn-back {
  background: #fff; border: 1px solid var(--border); color: var(--slate);
  padding: 6px 14px; border-radius: 6px; font-size: 13px;
}

.status-line { display: flex; gap: 16px; font-size: 13px; color: var(--slate); flex-wrap: wrap; }
.badge {
  background: rgba(217, 119, 87, 0.12); color: var(--accent);
  padding: 2px 10px; border-radius: 12px; font-weight: 500;
}

.kv { display: flex; gap: 8px; margin-bottom: 12px; font-size: 13px; align-items: flex-start; }
.kv b { color: var(--slate); font-weight: 500; min-width: 90px; flex-shrink: 0; }
.raw {
  background: var(--paper); padding: 10px 14px; border-radius: 6px; font-size: 12px;
  white-space: pre-wrap; word-break: break-word; margin: 0; flex: 1;
  font-family: inherit; border: 1px solid var(--border);
}

.round-select {
  padding: 6px 12px; border: 1px solid var(--border); border-radius: 6px;
  background: #fff; font-size: 13px;
}

.iteration { display: flex; flex-direction: column; gap: 20px; }
.qc-block { padding: 16px; background: var(--paper); border-radius: 8px; }
.scores { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 12px; }
.score-head { display: flex; justify-content: space-between; font-size: 13px; margin-bottom: 4px; }
.bar { height: 6px; background: var(--border); border-radius: 3px; overflow: hidden; }
.bar span { display: block; height: 100%; background: var(--accent); }
.comment { margin: 12px 0 0; font-size: 13px; color: var(--slate); }
.fix-list { margin: 8px 0 0; font-size: 13px; }
.fix-item { display: inline-block; margin: 2px 6px 0 0; padding: 2px 8px; background: var(--border); border-radius: 4px; font-size: 12px; }

.overall { font-size: 14px; color: var(--slate); margin: 0; }
.rewritten {
  background: var(--paper); padding: 14px; border-radius: 8px; font-size: 13px;
  line-height: 1.7; white-space: pre-wrap; word-break: break-word;
  font-family: inherit; border: 1px solid var(--border);
}

.empty { color: var(--slate); text-align: center; padding: 20px 0; }
.error {
  color: var(--danger); font-size: 13px; padding: 8px 12px;
  background: rgba(192, 72, 63, 0.08); border-radius: 6px;
}
</style>
