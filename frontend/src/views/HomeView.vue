<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import { createTask, iterateTask, stopTask } from '../api'
import { useTask } from '../composables/useTask'

const resumeText = ref('')
const jdText = ref('')
const userNotes = ref('')
const targetPosition = ref('')
const loading = ref(false)
const error = ref('')

const { state: taskState, setRecordId, startPolling, stopPolling, reset } = useTask()

const DRAFT_KEY = 'draft:form'

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
    })
  )
}

watch([resumeText, jdText, userNotes, targetPosition], saveDraft)

onMounted(() => {
  loadDraft()
  // 刷新后若有未完成任务，自动续接轮询
  if (taskState.currentRecordId) {
    startPolling(onTaskUpdate)
  }
})

onBeforeUnmount(stopPolling)

// ---- 提交任务 ----
const canSubmit = computed(() => resumeText.value.trim().length > 0 && !loading.value)

async function onSubmit() {
  error.value = ''
  loading.value = true
  try {
    const { data } = await createTask({
      resume_text: resumeText.value,
      jd_text: jdText.value,
      user_notes: userNotes.value,
      target_position: targetPosition.value,
    })
    setRecordId(data.record_id)
    startPolling(onTaskUpdate)
  } catch (e) {
    error.value = e.response?.data?.detail || e.message || '提交失败'
  } finally {
    loading.value = false
  }
}

function onTaskUpdate() {
  // polling 已在 useTask 中处理 state 更新，这里只需触发响应式
}

// ---- 迭代控制 ----
async function onIterate() {
  if (!taskState.currentRecordId) return
  error.value = ''
  loading.value = true
  try {
    await iterateTask(taskState.currentRecordId)
    startPolling(onTaskUpdate)
  } catch (e) {
    error.value = e.response?.data?.detail || '迭代失败'
  } finally {
    loading.value = false
  }
}

async function onStop() {
  if (!taskState.currentRecordId) return
  try {
    await stopTask(taskState.currentRecordId)
    stopPolling()
    // 触发一次状态拉取
    startPolling(onTaskUpdate)
    setTimeout(() => stopPolling(), 1500)
  } catch (e) {
    error.value = e.response?.data?.detail || '停止失败'
  }
}

// ---- 进度可视化 ----
const pipelineSteps = [
  { key: 'resume_parser', label: '简历解析者：抽取关键信息' },
  { key: 'jd_analyst', label: 'JD 分析师：拆解岗位要求' },
  { key: 'advisor', label: '求职简历顾问：诊断与建议' },
  { key: 'rewriter', label: '简历改写员：产出优化版简历' },
  { key: 'hr_qc', label: '模拟 HR 质检员：打分与质检' },
]

const STEP_ORDER = ['resume_parser', 'jd_analyst', 'advisor', 'rewriter', 'hr_qc']

const currentStepIndex = computed(() => {
  const step = taskState.status?.current_step
  if (!step) return -1
  return STEP_ORDER.indexOf(step)
})

// ---- 结果展示 ----
const latestIteration = computed(() => taskState.status?.latest_iteration || null)
const qcScores = computed(() => {
  const s = latestIteration.value?.final_qc?.scores || {}
  return [
    { label: '岗位匹配度', key: 'match_score' },
    { label: '关键词覆盖', key: 'keyword_score' },
    { label: '成果表达力', key: 'impact_score' },
    { label: '结构清晰度', key: 'clarity_score' },
    { label: '真实性', key: 'authenticity_score' },
  ].map(({ label, key }) => ({ label, value: Math.max(0, Math.min(100, Number(s[key]) || 0)) }))
})

const isRunning = computed(() => ['pending', 'running'].includes(taskState.status?.status) || (taskState.status?.status === 'iterating' && !!taskState.status?.current_step))
const canIterate = computed(() => {
  const st = taskState.status
  if (!st) return false
  return st.status === 'iterating' && st.current_round < st.max_rounds && !isRunning.value
})
const canStop = computed(() => {
  const st = taskState.status
  if (!st) return false
  return st.status === 'iterating' && !isRunning.value
})
const roundDisplay = computed(() => `${taskState.status?.current_round || 0}/${taskState.status?.max_rounds || 3}`)

// 开始新任务（清状态）
function newTask() {
  reset()
  taskState.status = null
}
</script>

<template>
  <div class="home">
    <!-- 输入区 -->
    <section class="card input-card" v-if="!taskState.status">
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
        {{ loading ? '提交中…' : '开始多 Agent 分析' }}
      </button>
      <p v-if="error" class="error">{{ error }}</p>
    </section>

    <!-- 任务执行中 -->
    <section v-else class="card pipeline-card">
      <div class="result-head">
        <h2>任务执行{{ isRunning ? '中' : '结果' }}</h2>
        <div class="round-badge">迭代进度 {{ roundDisplay }}</div>
      </div>

      <!-- 进度条 -->
      <ul class="steps">
        <li
          v-for="(step, i) in pipelineSteps"
          :key="step.key"
          :class="{
            done: isRunning ? i < currentStepIndex : i <= Math.max(currentStepIndex, pipelineSteps.length - 1),
            now: isRunning && i === currentStepIndex,
          }"
        >
          <span class="dot"></span>{{ step.label }}
        </li>
      </ul>

      <!-- 结果展示 -->
      <div v-if="latestIteration" class="result-body">
        <!-- HR 五维评分 -->
        <div class="qc-block">
          <h3>HR 质检评分</h3>
          <div class="scores">
            <div v-for="s in qcScores" :key="s.label" class="score">
              <div class="score-head"><span>{{ s.label }}</span><b>{{ s.value }}</b></div>
              <div class="bar"><span :style="{ width: s.value + '%' }"></span></div>
            </div>
          </div>
          <p v-if="latestIteration.final_qc?.comments" class="qc-comment">
            {{ latestIteration.final_qc.comments }}
          </p>
          <p v-if="latestIteration.fix_instructions?.length" class="fix-list">
            <b>修改意见：</b>
            <span v-for="(it, i) in latestIteration.fix_instructions" :key="i" class="fix-item">{{ it }}</span>
          </p>
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

      <!-- 错误展示 -->
      <p v-else-if="taskState.status?.error" class="error">{{ taskState.status.error }}</p>

      <!-- 迭代控制 -->
      <div class="actions" v-if="!isRunning">
        <button class="btn-primary" :disabled="!canIterate" @click="onIterate">
          继续迭代（{{ roundDisplay }}）
        </button>
        <button class="btn-secondary" :disabled="!canStop" @click="onStop">停止迭代</button>
        <button class="btn-text" @click="newTask">开始新任务</button>
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

.result-head {
  display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px;
}
.round-badge {
  background: rgba(217, 119, 87, 0.12); color: var(--accent); font-size: 13px;
  font-weight: 600; padding: 4px 12px; border-radius: 12px;
}

.steps { list-style: none; padding: 0; margin: 0 0 24px; display: flex; flex-direction: column; gap: 12px; }
.steps li {
  display: flex; align-items: center; gap: 10px; font-size: 14px; color: var(--slate);
  padding: 8px 12px; border-radius: 8px; background: var(--paper);
}
.steps li.done { color: var(--ink); }
.steps li.now { color: var(--accent); background: rgba(217, 119, 87, 0.08); font-weight: 500; }
.dot {
  width: 10px; height: 10px; border-radius: 50%; background: var(--border); flex-shrink: 0;
}
.done .dot { background: var(--success); }
.now .dot { background: var(--accent); box-shadow: 0 0 0 4px rgba(217, 119, 87, 0.2); }

.qc-block { margin-bottom: 24px; padding: 20px; background: var(--paper); border-radius: 10px; }
.qc-block h3 { font-size: 16px; margin-bottom: 14px; }
.scores { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 14px; }
.score-head { display: flex; justify-content: space-between; font-size: 13px; margin-bottom: 4px; }
.bar { height: 6px; background: var(--border); border-radius: 3px; overflow: hidden; }
.bar span { display: block; height: 100%; background: var(--accent); transition: width 0.3s; }
.qc-comment { margin: 14px 0 0; font-size: 13px; color: var(--slate); }
.fix-list { margin: 8px 0 0; font-size: 13px; color: var(--ink); }
.fix-item { display: inline-block; margin: 2px 6px 0 0; padding: 2px 8px; background: var(--border); border-radius: 4px; font-size: 12px; }

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
.btn-primary:disabled { opacity: 0.4; cursor: not-allowed; }
.btn-secondary {
  background: #fff; color: var(--danger); border: 1px solid var(--danger);
  padding: 10px 20px; border-radius: 8px; font-size: 14px;
}
.btn-secondary:disabled { opacity: 0.4; cursor: not-allowed; }
.btn-text {
  background: none; color: var(--slate); border: 1px solid var(--border);
  padding: 10px 20px; border-radius: 8px; font-size: 14px;
}

.error {
  color: var(--danger); font-size: 13px; padding: 8px 12px;
  background: rgba(192, 72, 63, 0.08); border-radius: 6px; margin: 12px 0 0;
}
</style>
