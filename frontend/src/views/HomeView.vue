<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import { analyze, getRecordDetail } from '../api'
import { useTask } from '../composables/useTask'

const resumeText = ref('')
const jdText = ref('')
const userNotes = ref('')
const targetPosition = ref('')
const formMode = ref('optimize') // 表单中选择的模式：optimize|compare
const loading = ref(false)
const error = ref('')

const { state: taskState, setRecordId, startPolling, stopPolling, reset } = useTask()

const DRAFT_KEY = 'draft:form'
const MAX_ROUNDS = 3

// 两种工作模式的说明（提交页卡片 + 结果页共用）
const MODE_DESC = {
  optimize: {
    name: '优化后测评',
    flow: '简历解析 → JD 分析 → 顾问诊断 → 简历改写 → HR 测评',
    detail: '自动优化原始简历，仅展示优化后简历与测评结果',
    eta: '2-5 分钟',
  },
  compare: {
    name: '前后对比测评',
    flow: '原始简历测评 → 顾问诊断 → 简历改写 → 优化后再次测评',
    detail: '先测评原始简历，优化后再次测评，直观对比分数与内容变化',
    eta: '3-7 分钟（多一次原始简历测评）',
  },
}

// 步骤定义：compare 模式在 JD 分析后多一步「原始简历测评」
const STEPS_FRONT = [
  { key: 'resume_parser', label: '简历解析' },
  { key: 'jd_analyst', label: 'JD 分析' },
]
const BASELINE_STEP = { key: 'baseline_qc', label: '原始简历测评' }
const STEPS_BACK = [
  { key: 'advisor', label: '顾问诊断' },
  { key: 'rewriter', label: '简历改写' },
  { key: 'hr_qc', label: 'HR 质检' },
]

// 任务执行后以后端返回的 mode 为准（刷新恢复场景），未提交时用表单选择
const activeMode = computed(() => taskState.status?.mode || formMode.value)
const isCompare = computed(() => activeMode.value === 'compare')

const STEPS = computed(() =>
  isCompare.value ? [...STEPS_FRONT, BASELINE_STEP, ...STEPS_BACK] : [...STEPS_FRONT, ...STEPS_BACK]
)
const STEP_ORDER = computed(() => STEPS.value.map(s => s.key))
const STEP_LABELS = computed(() => Object.fromEntries(STEPS.value.map(s => [s.key, s.label])))

// ---- 表单 localStorage 持久化 ----
function loadDraft() {
  try {
    const raw = localStorage.getItem(DRAFT_KEY)
    if (raw) {
      const d = JSON.parse(raw)
      resumeText.value = d.resume_text || ''
      jdText.value = d.jd_text || ''
      userNotes.value = d.user_notes || ''
      targetPosition.value = d.target_position || ''
      formMode.value = d.mode === 'compare' ? 'compare' : 'optimize'
    }
  } catch {}
}

function saveDraft() {
  localStorage.setItem(
    DRAFT_KEY,
    JSON.stringify({
      resume_text: resumeText.value,
      jd_text: jdText.value,
      user_notes: userNotes.value,
      target_position: targetPosition.value,
      mode: formMode.value,
    })
  )
}

watch([resumeText, jdText, userNotes, targetPosition, formMode], saveDraft)

onMounted(async () => {
  loadDraft()
  // 仅自动恢复「执行中」的任务；已完成/失败/不存在的旧任务不再盖住输入表单
  // （历史任务请到「历史记录」查看）
  if (taskState.currentRecordId) {
    try {
      const { data } = await getRecordDetail(taskState.currentRecordId)
      if (['pending', 'running'].includes(data.status)) {
        startPolling(() => {})
      } else {
        reset()
      }
    } catch {
      reset()
    }
  }
})

onBeforeUnmount(stopPolling)

// ---- 提交任务 ----
const canSubmit = computed(() => resumeText.value.trim().length > 0 && !loading.value)

async function onSubmit() {
  error.value = ''
  loading.value = true
  try {
    const { data } = await analyze({
      resume_text: resumeText.value,
      jd_text: jdText.value,
      user_notes: userNotes.value,
      target_position: targetPosition.value,
      mode: formMode.value,
    })
    setRecordId(data.record_id)
    startPolling(() => {})
  } catch (e) {
    error.value = e.response?.data?.detail || e.message || '提交失败'
  } finally {
    loading.value = false
  }
}

// ---- 步骤状态计算 ----
const currentStepName = computed(() => taskState.status?.current_step_name || taskState.status?.current_step || '')
const currentStepDesc = computed(() => taskState.status?.current_step_desc || '')
const iterationRound = computed(() => taskState.status?.iteration_round || 0)
const taskStatus = computed(() => taskState.status?.status || '')

const isRunning = computed(() => ['pending', 'running'].includes(taskStatus.value))
const isDone = computed(() => taskStatus.value === 'done')
const isError = computed(() => taskStatus.value === 'error')
const isCacheHit = computed(() => !!taskState.status?.cache_hit)
const failedStepLabel = computed(() => {
  const f = taskState.status?.failed_step || currentStepName.value
  return STEP_LABELS.value[f] || '未知'
})

// 每个步骤的状态：done / now / pending
function stepState(stepKey) {
  const order = STEP_ORDER.value
  if (isDone.value) return 'done'
  if (isError.value) {
    // 失败时，已执行的步骤标 done，其余 pending
    const failed = taskState.status?.failed_step || currentStepName.value
    const failedIdx = order.indexOf(failed)
    const idx = order.indexOf(stepKey)
    if (failedIdx >= 0 && idx < failedIdx) return 'done'
    return 'pending'
  }
  if (!isRunning.value) return 'pending'
  const curIdx = order.indexOf(currentStepName.value)
  const idx = order.indexOf(stepKey)
  if (curIdx < 0) return 'pending'
  if (idx < curIdx) return 'done'
  if (idx === curIdx) return 'now'
  return 'pending'
}

// ---- 结果展示 ----
const latestIteration = computed(() => {
  const iters = taskState.status?.iterations || []
  return iters.length > 0 ? iters[iters.length - 1] : null
})

const qcScores = computed(() => {
  const s = latestIteration.value?.final_qc?.scores || {}
  return DIMENSIONS.map(({ label, key, max }) => ({
    label,
    value: Math.max(0, Math.min(max, Number(s[key]) || 0)),
    max,
  }))
})

const overallScore = computed(() => {
  const s = latestIteration.value?.final_qc
  return s?.overall_score ?? null
})

// ---- compare 模式：优化前后对比 ----
const DIMENSIONS = [
  { label: 'JD 匹配度', key: 'jd_match', max: 35 },
  { label: '内容证据质量', key: 'evidence_quality', max: 25 },
  { label: '真实性边界', key: 'authenticity', max: 15 },
  { label: 'ATS 友好性', key: 'ats_friendly', max: 15 },
  { label: '可读性', key: 'readability', max: 10 },
]

const baselineQc = computed(() => taskState.status?.baseline_qc || null)
const baselineOverall = computed(() => baselineQc.value?.overall_score ?? null)
const originalResume = computed(() => taskState.status?.resume_text || '')

function clampScore(v, max) {
  const n = Math.max(0, Math.min(max, Number(v) || 0))
  return Math.round(n * 100) / 100
}

// 五维分数前后对比行
const compareRows = computed(() => {
  const before = baselineQc.value?.scores || {}
  const after = latestIteration.value?.final_qc?.scores || {}
  return DIMENSIONS.map(({ label, key, max }) => {
    const b = clampScore(before[key], max)
    const a = clampScore(after[key], max)
    return {
      label,
      max,
      before: b,
      after: a,
      delta: Math.round((a - b) * 100) / 100,
    }
  })
})

const overallDelta = computed(() => {
  if (baselineOverall.value == null || overallScore.value == null) return null
  // 四舍五入到两位小数，避免 1.2199999999999989 这类浮点尾数直接展示
  return Math.round((Number(overallScore.value) - Number(baselineOverall.value)) * 100) / 100
})

function deltaText(d) {
  if (d > 0) return `+${d}`
  if (d < 0) return `${d}`
  return '0'
}

// 预计耗时随模式变化
const etaText = computed(() => MODE_DESC[activeMode.value]?.eta || '2-5 分钟')

// 已运行时长格式化
const elapsedDisplay = computed(() => {
  const s = taskState.elapsed || 0
  const m = Math.floor(s / 60)
  const sec = s % 60
  return m > 0 ? `${m}分${sec}秒` : `${sec}秒`
})

// 开始新任务
function newTask() {
  reset()
}
</script>

<template>
  <div class="home">
    <!-- 输入区 -->
    <section class="card input-card" v-if="!taskState.status">
      <h2>填写简历与岗位</h2>

      <!-- 工作流程选择 -->
      <div class="mode-block">
        <span class="mode-block-title">选择测评方式</span>
        <div class="mode-picker">
          <div
            class="mode-card"
            :class="{ active: formMode === 'optimize' }"
            @click="formMode = 'optimize'"
          >
            <div class="mode-card-head">
              <span class="mode-radio">{{ formMode === 'optimize' ? '◉' : '○' }}</span>
              <b>选项一 · {{ MODE_DESC.optimize.name }}</b>
            </div>
            <p class="mode-flow">{{ MODE_DESC.optimize.flow }}</p>
            <p class="mode-detail">{{ MODE_DESC.optimize.detail }}</p>
            <p class="mode-eta">⏱️ 预计 {{ MODE_DESC.optimize.eta }}</p>
          </div>
          <div
            class="mode-card"
            :class="{ active: formMode === 'compare' }"
            @click="formMode = 'compare'"
          >
            <div class="mode-card-head">
              <span class="mode-radio">{{ formMode === 'compare' ? '◉' : '○' }}</span>
              <b>选项二 · {{ MODE_DESC.compare.name }}</b>
            </div>
            <p class="mode-flow">{{ MODE_DESC.compare.flow }}</p>
            <p class="mode-detail">{{ MODE_DESC.compare.detail }}</p>
            <p class="mode-eta">⏱️ 预计 {{ MODE_DESC.compare.eta }}</p>
          </div>
        </div>
      </div>

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
        {{ loading ? '提交中…' : '开始多 Agent 分析' }}
      </button>
      <p class="hint">提交后请勿重复点击，预计耗时 {{ etaText }}（缓存命中可秒级完成）</p>
      <p v-if="error" class="error">{{ error }}</p>
    </section>

    <!-- 任务执行中 / 结果 -->
    <section v-else class="card pipeline-card">
      <div class="result-head">
        <h2>{{ isDone ? '分析完成' : isError ? '分析失败' : '分析进行中' }}</h2>
        <div class="head-badges">
          <span class="mode-badge">{{ MODE_DESC[activeMode]?.name || '优化后测评' }}</span>
          <span class="round-badge">质检迭代 {{ iterationRound }}/{{ MAX_ROUNDS }} 轮</span>
        </div>
      </div>

      <!-- 缓存命中提示 -->
      <div v-if="isCacheHit" class="cache-hit">
        ✅ 检测到相同输入缓存，直接返回历史结果，跳过大模型调用
      </div>

      <!-- 耗时信息 -->
      <div class="timing">
        <span>⏱️ 预计耗时：{{ etaText }}</span>
        <span v-if="isRunning">已运行：{{ elapsedDisplay }}</span>
      </div>

      <!-- 步骤指示器（无百分比） -->
      <ul class="steps">
        <li
          v-for="step in STEPS"
          :key="step.key"
          :class="stepState(step.key)"
        >
          <span class="icon">
            <template v-if="stepState(step.key) === 'done'">✅</template>
            <template v-else-if="stepState(step.key) === 'now'">🔄</template>
            <template v-else>☐</template>
          </span>
          <span class="step-label">{{ step.label }}</span>
        </li>
      </ul>

      <!-- 当前步骤动态文案 -->
      <div v-if="isRunning && currentStepDesc" class="step-desc">
        {{ currentStepDesc }}
      </div>

      <!-- 错误展示 -->
      <div v-if="isError" class="error-block">
        <p class="error">
          分析失败（步骤：{{ failedStepLabel }}）
        </p>
        <p class="error-detail">{{ taskState.status?.error }}</p>
      </div>

      <!-- 结果展示：compare 模式（优化前后对比） -->
      <div v-if="isDone && latestIteration && isCompare" class="result-body">
        <!-- 总分对比 -->
        <div class="compare-hero">
          <div class="hero-side">
            <span class="hero-label">优化前 · 原始简历</span>
            <b class="hero-score">{{ baselineOverall ?? '—' }}</b>
            <span class="hero-total">/100</span>
          </div>
          <div class="hero-arrow">
            <span>➜</span>
            <span v-if="overallDelta != null" class="hero-delta" :class="overallDelta >= 0 ? 'up' : 'down'">
              {{ overallDelta >= 0 ? '提升' : '下降' }} {{ Math.abs(overallDelta) }} 分
            </span>
          </div>
          <div class="hero-side">
            <span class="hero-label">优化后简历</span>
            <b class="hero-score">{{ overallScore ?? '—' }}</b>
            <span class="hero-total">/100</span>
          </div>
        </div>

        <!-- 五维分数对比表（无百分比，仅分值与差值） -->
        <div class="qc-block">
          <h3>五维评分对比</h3>
          <table class="compare-table">
            <thead>
              <tr><th>评估维度</th><th>优化前</th><th>优化后</th><th>变化</th></tr>
            </thead>
            <tbody>
              <tr v-for="r in compareRows" :key="r.label">
                <td class="dim-name">{{ r.label }}</td>
                <td>{{ r.before }}/{{ r.max }}</td>
                <td><b>{{ r.after }}/{{ r.max }}</b></td>
                <td :class="r.delta > 0 ? 'up' : r.delta < 0 ? 'down' : 'flat'">
                  {{ deltaText(r.delta) }}
                </td>
              </tr>
            </tbody>
          </table>
          <p v-if="baselineQc?.comments" class="qc-comment">
            <b>优化前测评意见：</b>{{ baselineQc.comments }}
          </p>
          <p v-if="latestIteration.final_qc?.comments" class="qc-comment">
            <b>优化后测评意见：</b>{{ latestIteration.final_qc.comments }}
          </p>
        </div>

        <!-- 简历内容前后并排 -->
        <div class="resume-grid">
          <div class="block">
            <h3>原始简历</h3>
            <pre class="rewritten before">{{ originalResume }}</pre>
          </div>
          <div class="block">
            <h3>优化后简历（第 {{ latestIteration.round_number }} 轮）</h3>
            <pre class="rewritten after">{{ latestIteration.rewritten_resume }}</pre>
          </div>
        </div>

        <!-- 优化建议 -->
        <div v-if="latestIteration.optimization_advice" class="block">
          <h3>优化建议</h3>
          <p class="overall">{{ latestIteration.optimization_advice.overall_advice }}</p>
        </div>
      </div>

      <!-- 结果展示：optimize 模式（直接优化后测评） -->
      <div v-else-if="isDone && latestIteration" class="result-body">
        <!-- HR 五维评分 -->
        <div class="qc-block">
          <h3>HR 质检评分（总分 {{ overallScore }}/100）</h3>
          <div class="scores">
            <div v-for="s in qcScores" :key="s.label" class="score">
              <div class="score-head">
                <span>{{ s.label }}</span>
                <b>{{ s.value }}/{{ s.max }}</b>
              </div>
            </div>
          </div>
          <p v-if="latestIteration.final_qc?.comments" class="qc-comment">
            {{ latestIteration.final_qc.comments }}
          </p>
          <div v-if="latestIteration.final_qc?.strengths?.length" class="qc-list">
            <b>优点：</b>
            <span v-for="(it, i) in latestIteration.final_qc.strengths" :key="i" class="tag good">{{ it }}</span>
          </div>
          <div v-if="latestIteration.final_qc?.weaknesses?.length" class="qc-list">
            <b>不足：</b>
            <span v-for="(it, i) in latestIteration.final_qc.weaknesses" :key="i" class="tag warn">{{ it }}</span>
          </div>
        </div>

        <!-- 优化建议 -->
        <div v-if="latestIteration.optimization_advice" class="block">
          <h3>优化建议</h3>
          <p class="overall">{{ latestIteration.optimization_advice.overall_advice }}</p>
        </div>

        <!-- 改写后简历 -->
        <div v-if="latestIteration.rewritten_resume" class="block">
          <h3>优化后简历（第 {{ latestIteration.round_number }} 轮）</h3>
          <pre class="rewritten">{{ latestIteration.rewritten_resume }}</pre>
        </div>
      </div>

      <!-- 操作 -->
      <div class="actions" v-if="isDone || isError">
        <button class="btn-primary" @click="newTask">开始新任务</button>
        <button class="btn-text" @click="() => { reset(); }">返回编辑</button>
      </div>
      <p v-if="error" class="error">{{ error }}</p>
    </section>
  </div>
</template>

<style scoped>
.home { display: flex; flex-direction: column; gap: 20px; }

.card {
  background: var(--card);
  border-radius: 12px;
  border: 1px solid var(--border);
  padding: 28px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.04);
}

.input-card h2, .pipeline-card h2 { font-size: 20px; margin-bottom: 20px; }

.field { display: flex; flex-direction: column; gap: 6px; margin-bottom: 16px; }
.field span { font-size: 13px; color: var(--slate); font-weight: 500; }
.field span em { color: var(--danger); font-style: normal; }
.field input, .field textarea {
  padding: 10px 12px; border: 1px solid var(--border); border-radius: 8px;
  background: #fff; resize: vertical;
}
.field input:focus, .field textarea:focus { outline: none; border-color: var(--accent); }

.submit {
  background: var(--ink); color: #fff; border: none; padding: 12px 24px;
  border-radius: 8px; font-size: 15px; font-weight: 500; margin-top: 8px;
}
.submit:disabled { opacity: 0.5; cursor: not-allowed; }
.hint { font-size: 12px; color: var(--slate); margin-top: 8px; }

.result-head {
  display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px;
}
.round-badge {
  background: rgba(217, 119, 87, 0.12); color: var(--accent); font-size: 13px;
  font-weight: 600; padding: 4px 12px; border-radius: 12px;
}

.cache-hit {
  background: rgba(47, 125, 90, 0.1); color: var(--success);
  padding: 10px 14px; border-radius: 8px; font-size: 13px; font-weight: 500;
  margin-bottom: 16px;
}

.timing {
  display: flex; gap: 20px; font-size: 13px; color: var(--slate); margin-bottom: 16px;
}

/* 步骤指示器：无百分比，仅状态符号 */
.steps { list-style: none; padding: 0; margin: 0 0 16px; display: flex; flex-direction: column; gap: 10px; }
.steps li {
  display: flex; align-items: center; gap: 12px; font-size: 14px; color: var(--slate);
  padding: 10px 14px; border-radius: 8px; background: var(--paper);
  transition: all 0.2s;
}
.steps li.done { color: var(--ink); }
.steps li.now { color: var(--accent); background: rgba(217, 119, 87, 0.08); font-weight: 500; }
.steps li .icon { font-size: 16px; width: 22px; text-align: center; flex-shrink: 0; }
.steps li .step-label { flex: 1; }

.step-desc {
  font-size: 13px; color: var(--slate); padding: 10px 14px;
  background: var(--paper); border-radius: 8px; margin-bottom: 16px;
  border-left: 3px solid var(--accent);
}

.error-block { margin-bottom: 16px; }
.error-detail { font-size: 13px; color: var(--slate); margin-top: 4px; }

.qc-block { margin-bottom: 24px; padding: 20px; background: var(--paper); border-radius: 10px; }
.qc-block h3 { font-size: 16px; margin-bottom: 14px; }
.scores { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 14px; }
.score-head { display: flex; justify-content: space-between; font-size: 13px; margin-bottom: 4px; }
.score b { color: var(--accent); }
.qc-comment { margin: 14px 0 0; font-size: 13px; color: var(--slate); }
.qc-list { margin: 10px 0 0; font-size: 13px; }
.qc-list b { display: block; margin-bottom: 4px; }
.tag { display: inline-block; margin: 2px 6px 0 0; padding: 2px 8px; border-radius: 4px; font-size: 12px; }
.tag.good { background: rgba(47, 125, 90, 0.12); color: var(--success); }
.tag.warn { background: rgba(192, 72, 63, 0.1); color: var(--danger); }

.block { margin-bottom: 24px; }
.block h3 { font-size: 16px; margin-bottom: 10px; }
.overall { font-size: 14px; color: var(--slate); margin: 0; }
.rewritten {
  background: var(--paper); padding: 16px; border-radius: 8px; font-size: 13px;
  line-height: 1.7; white-space: pre-wrap; word-break: break-word;
  font-family: inherit; border: 1px solid var(--border);
}

.actions {
  display: flex; gap: 12px; margin-top: 24px; padding-top: 20px;
  border-top: 1px solid var(--border); flex-wrap: wrap;
}
.btn-primary {
  background: var(--ink); color: #fff; border: none; padding: 10px 20px;
  border-radius: 8px; font-size: 14px; font-weight: 500;
}
.btn-text {
  background: none; color: var(--slate); border: 1px solid var(--border);
  padding: 10px 20px; border-radius: 8px; font-size: 14px;
}

.error {
  color: var(--danger); font-size: 13px; padding: 8px 12px;
  background: rgba(192, 72, 63, 0.08); border-radius: 6px; margin: 12px 0 0;
}

/* ---- 模式选择卡片 ---- */
.mode-block { margin-bottom: 20px; }
.mode-block-title { display: block; font-size: 13px; color: var(--slate); font-weight: 500; margin-bottom: 8px; }
.mode-picker { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.mode-card {
  border: 1.5px solid var(--border); border-radius: 10px; padding: 14px 16px;
  cursor: pointer; transition: all 0.15s; background: #fff;
}
.mode-card:hover { border-color: var(--slate); }
.mode-card.active { border-color: var(--accent); background: rgba(217, 119, 87, 0.05); }
.mode-card-head { display: flex; align-items: center; gap: 8px; font-size: 14px; margin-bottom: 8px; }
.mode-card.active .mode-card-head b { color: var(--accent); }
.mode-radio { color: var(--accent); font-size: 15px; }
.mode-flow { font-size: 12px; color: var(--ink); margin: 0 0 6px; line-height: 1.5; }
.mode-detail { font-size: 12px; color: var(--slate); margin: 0 0 8px; line-height: 1.5; }
.mode-eta { font-size: 12px; color: var(--slate); margin: 0; }

.head-badges { display: flex; gap: 8px; align-items: center; }
.mode-badge {
  background: rgba(70, 90, 120, 0.1); color: var(--slate); font-size: 12px;
  font-weight: 600; padding: 4px 12px; border-radius: 12px;
}

/* ---- compare 模式：总分对比 ---- */
.compare-hero {
  display: flex; align-items: center; justify-content: center; gap: 28px;
  padding: 24px 20px; background: var(--paper); border-radius: 10px; margin-bottom: 20px;
}
.hero-side { display: flex; flex-direction: column; align-items: center; gap: 2px; }
.hero-label { font-size: 13px; color: var(--slate); }
.hero-score { font-size: 40px; font-weight: 700; line-height: 1.1; color: var(--ink); }
.hero-total { font-size: 13px; color: var(--slate); }
.hero-arrow { display: flex; flex-direction: column; align-items: center; gap: 6px; font-size: 24px; color: var(--slate); }
.hero-delta { font-size: 13px; font-weight: 600; white-space: nowrap; }
.up { color: var(--success); }
.down { color: var(--danger); }
.flat { color: var(--slate); }

/* ---- 五维对比表（分值，无百分比） ---- */
.compare-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.compare-table th, .compare-table td {
  padding: 8px 10px; border-bottom: 1px solid var(--border); text-align: center;
}
.compare-table th { color: var(--slate); font-weight: 500; background: #fff; }
.compare-table td.dim-name { text-align: left; color: var(--ink); }

/* ---- 简历前后并排（窄屏堆叠） ---- */
.resume-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 24px; }
.resume-grid .block { margin-bottom: 0; }
.resume-grid .rewritten { max-height: 560px; overflow-y: auto; }
pre.rewritten.before { background: #f6f6f5; }
pre.rewritten.after { border-color: rgba(47, 125, 90, 0.35); }

@media (max-width: 860px) {
  .mode-picker { grid-template-columns: 1fr; }
  .resume-grid { grid-template-columns: 1fr; }
}
</style>
