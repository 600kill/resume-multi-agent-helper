<script setup>
import { ref, computed } from 'vue'
import { analyzeResume, checkHealth } from './api'

const resumeText = ref('')
const jdText = ref('')
const userNotes = ref('')
const targetPosition = ref('')
const loading = ref(false)
const error = ref('')
const result = ref(null)
const pipelineStep = ref(0)

const pipelineSteps = [
  '简历解析者：抽取简历关键信息',
  'JD 分析师：拆解岗位要求',
  '求职简历顾问：诊断差距并给出建议',
  '简历改写员：产出优化版简历',
  '模拟 HR 质检员：打分与质检',
]

const healthOk = ref(false)
checkHealth().then(() => (healthOk.value = true)).catch(() => (healthOk.value = false))

const canSubmit = computed(() => resumeText.value.trim().length > 0 && !loading.value)

async function onSubmit() {
  error.value = ''
  loading.value = true
  pipelineStep.value = 0

  // 模拟分阶段进度展示（真实执行在服务端完成）
  const timer = setInterval(() => {
    pipelineStep.value = Math.min(pipelineStep.value + 1, pipelineSteps.length - 1)
  }, 1600)

  try {
    const res = await analyzeResume({
      resume_text: resumeText.value,
      jd_text: jdText.value,
      user_notes: userNotes.value,
      target_position: targetPosition.value,
    })
    result.value = res.data
  } catch (e) {
    error.value = (e.response?.data?.error) || e.message || '分析失败，请重试'
    result.value = null
  } finally {
    clearInterval(timer)
    loading.value = false
  }
}

function scorePercent(v) {
  return Math.max(0, Math.min(100, Number(v) || 0))
}

function qcScores() {
  const s = result.value?.final_qc?.scores || {}
  return [
    { label: '岗位匹配度', key: 'match_score' },
    { label: '关键词覆盖', key: 'keyword_score' },
    { label: '成果表达力', key: 'impact_score' },
    { label: '结构清晰度', key: 'clarity_score' },
    { label: '真实性', key: 'authenticity_score' },
  ].map(({ label, key }) => ({ label, value: scorePercent(s[key]) }))
}

const hasResult = computed(() => !!result.value && !result.value.error)
</script>

<template>
  <div class="shell">
    <header class="topbar">
      <div class="brand">
        <span class="logo">cv</span>
        <div>
          <h1>简历多智能体优化助手</h1>
          <p class="tagline">五个 AI 顾问，为你的简历把好每一关</p>
        </div>
      </div>
      <span class="health" :class="healthOk ? 'ok' : 'off'">
        {{ healthOk ? '服务在线' : '服务离线' }}
      </span>
    </header>

    <main class="layout">
      <!-- 输入区 -->
      <section class="card input-card">
        <h2>填写简历与岗位</h2>
        <label class="field">
          <span>目标岗位（可选）</span>
          <input v-model="targetPosition" placeholder="如：大模型应用开发实习生" />
        </label>
        <label class="field">
          <span>简历原文 <em>*</em></span>
          <textarea v-model="resumeText" rows="8" placeholder="粘贴你的简历内容…"></textarea>
        </label>
        <label class="field">
          <span>岗位 JD（可选）</span>
          <textarea v-model="jdText" rows="5" placeholder="粘贴目标岗位的职位描述…"></textarea>
        </label>
        <label class="field">
          <span>你的补充建议（可选）</span>
          <textarea v-model="userNotes" rows="3" placeholder="如：我偏向前端方向 / 想突出某个项目…"></textarea>
        </label>
        <button class="submit" :disabled="!canSubmit" @click="onSubmit">
          {{ loading ? '分析中…' : '开始多 Agent 分析' }}
        </button>
        <p v-if="error" class="error">{{ error }}</p>
      </section>

      <!-- 进度区 -->
      <section v-if="loading" class="card pipeline-card">
        <h2>多 Agent 流水线执行中</h2>
        <ul class="steps">
          <li v-for="(step, i) in pipelineSteps" :key="i" :class="{ done: i < pipelineStep, now: i === pipelineStep }">
            <span class="dot"></span>{{ step }}
          </li>
        </ul>
      </section>

      <!-- 结果区 -->
      <section v-else-if="hasResult" class="card result-card">
        <div class="result-head">
          <h2>分析报告</h2>
          <span v-if="result.record_id" class="rid">#{{ result.record_id }}</span>
        </div>

        <!-- 质检打分 -->
        <div class="qc-block">
          <h3>HR 质检评分</h3>
          <div class="scores">
            <div v-for="s in qcScores()" :key="s.label" class="score">
              <div class="score-head"><span>{{ s.label }}</span><b>{{ s.value }}</b></div>
              <div class="bar"><span :style="{ width: s.value + '%' }"></span></div>
            </div>
          </div>
          <p v-if="result.final_qc?.comments" class="qc-comment">{{ result.final_qc.comments }}</p>
        </div>

        <!-- JD 分析 -->
        <div v-if="result.jd_analysis" class="block">
          <h3>JD 分析</h3>
          <ul class="kw-list">
            <li v-for="(k, i) in (result.jd_analysis.keywords || [])" :key="i" class="kw">{{ k }}</li>
          </ul>
        </div>

        <!-- 优化建议 -->
        <div v-if="result.optimization_advice" class="block">
          <h3>优化建议</h3>
          <p class="overall">{{ result.optimization_advice.overall_advice }}</p>
          <div v-for="(item, i) in (result.optimization_advice.improvement_suggestions || [])" :key="i" class="advice">
            <b>{{ item.section || '建议 ' + (i + 1) }}</b>
            <p class="issue">问题：{{ item.issue }}</p>
            <p class="sug">建议：{{ item.suggestion }}</p>
          </div>
        </div>

        <!-- 改写后简历 -->
        <div v-if="result.rewritten_resume" class="block">
          <h3>优化后简历</h3>
          <pre class="rewritten">{{ result.rewritten_resume }}</pre>
        </div>
      </section>

      <!-- 空态 -->
      <section v-else class="card empty-card">
        <p>输入简历内容，点击「开始多 Agent 分析」。</p>
        <p class="hint">系统会依次调用简历解析者、JD 分析师、求职简历顾问、简历改写员、模拟 HR 质检员五个 AI，为你生成诊断与优化版简历。</p>
      </section>
    </main>
  </div>
</template>

<style scoped>
.shell {
  max-width: 1240px;
  margin: 0 auto;
  padding: 24px 20px 48px;
}
.topbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 20px;
  border-bottom: 1px solid var(--border);
  margin-bottom: 24px;
}
.brand {
  display: flex;
  align-items: center;
  gap: 14px;
}
.logo {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  background: var(--ink);
  color: var(--paper);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 18px;
  letter-spacing: 0.5px;
}
.topbar h1 {
  font-size: 20px;
}
.tagline {
  margin: 2px 0 0;
  color: var(--slate);
  font-size: 13px;
}
.health {
  font-size: 13px;
  padding: 4px 12px;
  border-radius: 999px;
  border: 1px solid var(--border);
}
.health.ok {
  color: var(--success);
  border-color: #cfe4d8;
  background: #f0f7f2;
}
.health.off {
  color: var(--danger);
  border-color: #ecd4d0;
  background: #faf0ee;
}
.layout {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
  align-items: start;
}
.card {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 22px;
}
.card h2 {
  font-size: 16px;
  margin-bottom: 16px;
}
.field {
  display: block;
  margin-bottom: 14px;
}
.field > span {
  display: block;
  font-size: 13px;
  margin-bottom: 6px;
  color: var(--slate);
}
.field em {
  color: var(--danger);
  font-style: normal;
}
.field input,
.field textarea {
  width: 100%;
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 10px 12px;
  resize: vertical;
  background: #fdfcfa;
}
.field input:focus,
.field textarea:focus {
  outline: none;
  border-color: var(--accent);
}
.submit {
  width: 100%;
  padding: 12px;
  background: var(--accent);
  color: #fff;
  border: none;
  border-radius: 8px;
  font-size: 15px;
  font-weight: 600;
  transition: opacity 0.2s;
}
.submit:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.error {
  margin-top: 12px;
  color: var(--danger);
  font-size: 13px;
}
.steps {
  list-style: none;
  padding: 0;
  margin: 0;
}
.steps li {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 0;
  color: var(--slate);
  font-size: 14px;
}
.dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  border: 2px solid var(--border);
  flex-shrink: 0;
}
.steps li.done .dot {
  background: var(--success);
  border-color: var(--success);
}
.steps li.now .dot {
  border-color: var(--accent);
  background: var(--accent);
  animation: pulse 1s infinite;
}
.steps li.now {
  color: var(--ink);
  font-weight: 600;
}
@keyframes pulse {
  50% {
    transform: scale(1.2);
  }
}
.result-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.rid {
  font-size: 12px;
  color: var(--slate);
}
.block {
  margin-top: 18px;
  padding-top: 16px;
  border-top: 1px dashed var(--border);
}
.block h3 {
  font-size: 14px;
  margin-bottom: 10px;
  color: var(--ink);
}
.kw-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding: 0;
  margin: 0;
  list-style: none;
}
.kw {
  background: #eef1f5;
  color: var(--ink);
  font-size: 13px;
  padding: 4px 10px;
  border-radius: 999px;
}
.overall {
  color: var(--ink);
  font-weight: 600;
  font-size: 14px;
}
.advice {
  margin-top: 10px;
  padding: 10px 12px;
  background: #fdf6f2;
  border-radius: 8px;
}
.advice b {
  font-size: 13px;
}
.issue {
  margin: 4px 0;
  color: var(--danger);
  font-size: 13px;
}
.sug {
  margin: 4px 0 0;
  color: var(--slate);
  font-size: 13px;
}
.rewritten {
  white-space: pre-wrap;
  background: #fbf9f4;
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 14px;
  font-size: 13px;
  line-height: 1.7;
  color: var(--ink);
}
.qc-block h3 {
  font-size: 14px;
}
.scores {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-top: 12px;
}
.score-head {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
  color: var(--slate);
}
.score-head b {
  color: var(--ink);
}
.bar {
  height: 6px;
  background: #eee9df;
  border-radius: 3px;
  margin-top: 6px;
  overflow: hidden;
}
.bar span {
  display: block;
  height: 100%;
  background: var(--accent);
}
.qc-comment {
  margin-top: 12px;
  font-size: 13px;
  color: var(--slate);
}
.empty-card {
  color: var(--slate);
  font-size: 14px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  min-height: 200px;
}
.hint {
  color: var(--slate);
  opacity: 0.75;
}
@media (max-width: 860px) {
  .layout {
    grid-template-columns: 1fr;
  }
}
</style>