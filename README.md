# 简历多智能体优化助手

输入简历原文、目标岗位 JD 和个人诉求，由 **LangGraph 编排的 5 个 AI Agent** 自动完成
「解析 → 岗位分析 → 优化建议 → 简历改写 → HR 质检」，质检不达标会带着具体修改意见**自动打回改写、最多迭代 3 轮**，
最终产出量化评分报告与岗位定制版简历。

系统提供**两种工作流程**，提交时一键选择：

- **选项一 · 优化后测评**：直接优化原始简历，输出优化稿 + HR 测评结果（约 2–5 分钟）
- **选项二 · 前后对比测评**：先测评原始简历 → 自动优化 → 再次测评，同屏展示优化前后的简历原文与五维评分差值，直观看到提分效果（约 3–7 分钟）

- 后端：Python · FastAPI · LangGraph · RQ（异步任务队列）· PostgreSQL · Redis
- 前端：Vue 3 · Vite · Axios（开发环境 5173 端口代理后端；构建产物也可由 FastAPI 同端口托管）
- LLM：OpenAI 兼容接口（当前接入 `glm-4.6v`，经本地 CC Switch / Codex 客户端转发），换模型只改配置

## 实测对比数据（前后对比测评模式）

三组不同基线水平的真实样本，HR 五维评分（满分 100）优化前后对比：

| 样本类型 | 优化前得分 | 优化后得分 | 净提升 | 核心亮点 |
|---|---|---|---|---|
| 样本 A（高基线） | 88 | 89.22 | +1.22 | 在高分基础上进一步微调 JD 匹配度 |
| 样本 B（技术匹配） | 85 | 97 | +12 | JD 匹配度达满分，多维度全面提升 |
| 样本 C（潜力股） | 85 | 100 | +15 | 实现满分优化，JD 匹配度 +10、证据质量 +5 |
| **平均值** | **86** | **95.4** | **+9.4** | 平均提升近 10 分，最高达满分 |

> 评分由 HR 质检 Agent 独立给出，每个维度必须引用简历原文作为证据，优化前后使用同一套评分标准；
> 五维分值与差值在前端以「分数/满分」形式展示，不使用百分比进度条。

典型样本（样本 C）五维变化：JD 匹配度 25/35 → 35/35（+10）、内容证据质量 20/25 → 25/25（+5），
真实性边界始终保持满分 15/15——改写遵循证据优先原则，只重组已有事实，不编造指标。

## 实际运行截图

**① 首页：两种测评方式卡片 + 填写简历 / JD**

![首页](docs/images/01-home.png)

**② 提交后：步骤指示器实时推进（✅完成 / 🔄运行中 / ☐待执行，无百分比假进度）**

![执行中](docs/images/02-running.png)

**③ 分析报告：HR 五维评分、JD 关键词匹配、逐条优化建议**

![分析报告](docs/images/03-report.png)

**④ 优化后简历：面向目标岗位重写，量化成果前置（XYZ 结构、ATS 友好 Markdown）**

![优化后简历](docs/images/05-rewritten.png)

**⑤ 自动生成的 OpenAPI 接口文档（`/docs`）**

![API 文档](docs/images/04-api-docs.png)

## 两种工作流程

```
选项一 · 优化后测评（5 步）
  简历解析 ┐
           ├─▶ 顾问诊断 ─▶ 简历改写 ─▶ HR 质检 ─▶ 结果
  JD 分析 ┘

选项二 · 前后对比测评（6 步，仅多 1 次 LLM 调用）
  简历解析 ┐
           ├─▶ 原始简历基线测评 ─▶ 顾问诊断 ─▶ 简历改写 ─▶ HR 质检
  JD 分析 ┘                                                    │
           ◀──── 质检不通过：携带 fix_instructions 打回（≤3 轮）◀┘
```

- 两种模式由 `AgentState.mode`（`optimize` / `compare`）驱动，同一张 LangGraph 图实现；
  选项一中基线测评节点是纯 pass-through，**不产生额外 LLM 调用**。
- 选项二完成后，结果页展示：优化前后总分对比卡（如 85 ➜ 100 提升 15 分）、五维分值差值表、
  优化前后简历左右并排、两版 HR 测评意见。
- Redis 缓存 key 包含模式字段，两种模式互不串用。

## 多 Agent 流水线

| Agent | System Prompt 核心规则 | 产出 |
|---|---|---|
| ① 简历解析者 | 严格结构化 JSON；项目拆出背景/本人角色/模块/技术栈/已有指标；忠于原文不脑补；标记全部可量化素材 | 基本信息/教育/经历/项目/技能/工具 JSON |
| ② JD 分析师 | 三级拆解 **Must-Have / Should-Have / Nice-to-Have**；每条含关键词 + 岗位行为描述，区分工具要求与业务任务 | 三级分类报告 + 候选人画像 |
| ③ 求职简历顾问 | 诊断 Must-Have 证据缺口与未充分利用的 Should-Have 素材；仅用简历已有事实；XYZ 评估项目，标记弱动词与缺失量化点 | 差距诊断 + 逐条修改建议（含修改位置与方向） |
| ④ 简历改写员 | 证据优先严禁编造；技术项目优先 XYZ 模型、STAR 仅用于非技术实习；强主动动词；F-Pattern 数字前置；每条一事一叙 ≤2 行；关键词须带上下文；ATS 友好 Markdown | 岗位定制版完整简历 |
| ⑤ 模拟 HR 质检员 | 打分必须引用简历原文证据；输出 fix_instructions 打回改写；双重门槛判定 | 五维评分、通过标记、修改清单 |

**HR 五维评分模型（总分 100）**：

| 维度 | 满分 | 考察点 |
|---|---|---|
| JD 匹配度 | 35 | Must-Have / Should-Have 证据覆盖 |
| 内容证据质量 | 25 | 量化成果、项目细节是否扎实 |
| 真实性边界 | 15 | 是否存在编造指标、拔高角色 |
| ATS 友好性 | 15 | 关键词覆盖、格式是否可解析 |
| 可读性 | 10 | 结构、动词、F-Pattern 阅读体验 |

**通过判定**：`overall_score ≥ 75` **且** `authenticity ≥ 12`（防止为冲分编造指标）。

**质检回环**：⑤ 不通过时把结构化修改意见写入状态打回 ④，改写员在下一轮 prompt 中逐条编号落实，
HR 复核时对照上轮意见验收；达到 3 轮上限自动结束并返回最后一稿，防止死循环。轮次对外可见（「质检迭代 N/3 轮」）。

## 技术栈与目录

```
projects/
├─ backend/
│  ├─ app/
│  │  ├─ main.py              # FastAPI 入口（CORS、同端口托管前端 dist）
│  │  ├─ config.py            # 全部配置（RESUME_ 前缀环境变量）
│  │  ├─ auth.py              # JWT 签发/校验 + bcrypt 密码哈希
│  │  ├─ llm.py               # LLM 封装：仅暴露 ask / ask_json，换模型只改这里
│  │  ├─ cache.py             # Redis：统一 key 工具 + HIT/MISS 日志 + TTL
│  │  ├─ db.py / models.py    # SQLAlchemy + PostgreSQL（users / analysis_records / iterations）
│  │  ├─ worker.py            # RQ 任务定义：enqueue_analysis / run_analysis_job
│  │  ├─ migrate_db.py        # 表结构增量迁移（幂等，可重复执行）
│  │  ├─ api/                 # 认证、健康检查、analyze / records 路由（含资源归属校验）
│  │  └─ agents/              # 5 个 Agent + state.py + graph.py + service.py
│  │     ├─ state.py          # AgentState：步骤名/步骤文案/迭代轮次/时间戳/工作模式
│  │     ├─ graph.py          # LangGraph：并行 fan-in、基线测评、条件路由回环
│  │     └─ service.py        # 缓存检查 → stream 执行 → 每节点落库 → 失败步骤捕获
│  ├─ run_worker.py           # RQ Worker 启动入口
│  └─ .env                    # 本地配置（不入库）
├─ frontend/                  # Vue 3 + Vite 源码，构建到 frontend/dist
├─ docs/images/               # 本文档使用的实际运行截图
└─ README.md
```

## 本地运行（Windows + Docker）

### 1. 启动 PostgreSQL 与 Redis（Docker）

本机 5432 若被其他服务占用，PostgreSQL 映射到 **5433**：

```powershell
docker run -d --name resume-agent-pg --restart unless-stopped `
  -e POSTGRES_USER=resume -e POSTGRES_PASSWORD=resume -e POSTGRES_DB=resume_agent `
  -p 127.0.0.1:5433:5432 `
  docker.1ms.run/library/postgres:16-alpine

docker run -d --name resume-agent-redis --restart unless-stopped `
  -p 127.0.0.1:6379:6379 `
  docker.1ms.run/library/redis:7-alpine
```

表结构由 SQLAlchemy 在服务启动时自动创建；后续新增字段执行一次幂等迁移：

```powershell
cd backend
..\.venv\Scripts\python.exe -m app.migrate_db
```

### 2. 安装依赖、构建前端

```powershell
# Python 依赖（项目根目录，使用 uv 管理的 .venv）
uv sync

# 前端依赖与构建（无 pnpm 时可用 corepack pnpm）
cd frontend
pnpm install
pnpm build
cd ..
```

### 3. 配置 `backend/.env`

```ini
RESUME_DATABASE_URL=postgresql://resume:resume@127.0.0.1:5433/resume_agent
RESUME_REDIS_URL=redis://127.0.0.1:6379/0

# OpenAI 兼容 LLM 端点（示例：本地 CC Switch / Codex 代理）
RESUME_MODEL=glm-4.6v
RESUME_LLM_BASE_URL=http://127.0.0.1:15721/v1
RESUME_LLM_API_KEY=ccswitch-local
RESUME_LLM_TIMEOUT=180
```

> 接入其他 OpenAI 兼容服务（含云端）时，只需替换 `MODEL / BASE_URL / API_KEY` 三项；
> 5 个 Agent 与图编排代码完全不感知具体模型。

### 4. 启动后端 API、RQ Worker 并访问

需要**两个进程**：API 服务负责接收请求，Worker 进程负责后台跑 LangGraph。

```powershell
# 终端 1：API
cd backend
..\.venv\Scripts\uvicorn.exe app.main:app --host 127.0.0.1 --port 5000

# 终端 2：RQ Worker（同样在 backend 目录）
..\.venv\Scripts\python.exe run_worker.py
```

- 生产式访问（FastAPI 托管前端构建产物）：http://127.0.0.1:5000
- 开发模式（热更新，Vite 代理 /api → 5000）：`cd frontend; pnpm dev` → http://127.0.0.1:5173
- 接口文档：http://127.0.0.1:5000/docs

## HTTP 接口

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/auth/register` `/api/auth/login` | 注册 / 登录（bcrypt 哈希，返回 JWT） |
| GET | `/api/health` | 服务健康检查（前端右上角状态灯） |
| POST | `/api/analyze` | **异步**：建记录 + 入队 RQ，立即返回 `{record_id, task_id}` |
| GET | `/api/records` | 历史分析记录列表（状态、岗位、测评方式、评分、时间） |
| GET | `/api/records/{record_id}` | 轮询单条任务：步骤名/步骤文案/迭代轮次/失败步骤/缓存命中/各 Agent 结果（含资源归属校验） |

`POST /api/analyze` 请求体新增 `mode` 字段：`optimize`（默认，选项一）或 `compare`（选项二），非法值返回 422。
接口立即响应不阻塞；前端按 2 秒间隔轮询 `GET /api/records/{id}`，任务终态（done/error）自动停止。

## 工程要点

**异步任务架构**：FastAPI 收到请求后只做建库记录 + RQ 入队，立即返回 `record_id`；
LangGraph 在独立 Worker 进程执行，LLM 慢（2–7 分钟）不占用 API 连接、不阻塞其他请求。

**步骤状态严格一致（禁止伪造进度）**：`AgentState` 携带 `current_step_name / current_step_desc /
iteration_round / step_timestamp`，以 `stream_mode="updates"` 逐节点消费图事件，**每个节点执行完毕即落库 PG + Redis**。
前端步骤指示器的 ✅/🔄/☐ 全部由真实步骤推导，无百分比进度条；质检回环轮次对外暴露。

**Redis 结果缓存**：

- key：`resume:v1:analyze:{sha256}`，哈希内容为五项输入（简历/JD/诉求/岗位/**模式**）按 key 排序后的 JSON，参数顺序不影响命中；
- TTL 3600 秒；命中时记录标记 `cache_hit=true`、跳过全部 LLM 调用、秒级完成，前端显示「✅ 检测到相同输入缓存，直接返回历史结果，跳过大模型调用」；
- Redis 不可用时自动降级为无缓存，不阻断服务。

**异常处理不静默崩溃**：LLM 超时 / 502 / 连接失败等异常在节点级捕获，落库
`status=error + failed_step`，前端明确显示失败步骤中文名与友好中文提示；原始堆栈只进后端日志，不暴露给用户。

**安全基线**：bcrypt 密码哈希、JWT 鉴权、所有记录查询校验 `user_id` 归属防越权、`.env` 不入库。

## 配置项一览（均带 `RESUME_` 前缀，见 `backend/app/config.py`）

| 配置 | 默认值 | 说明 |
|---|---|---|
| `DATABASE_URL` | `postgresql://resume:resume@127.0.0.1:5432/resume_agent` | PostgreSQL 连接串 |
| `REDIS_URL` | `redis://127.0.0.1:6379/0` | Redis 连接串（缓存 + RQ 队列共用） |
| `MODEL` | `glm-4.6v` | LLM 模型名 |
| `LLM_BASE_URL` | `http://127.0.0.1:15721/v1` | OpenAI 兼容端点 |
| `LLM_API_KEY` | `ccswitch-local` | API Key（本地代理占位即可） |
| `LLM_TIMEOUT` / `LLM_MAX_TOKENS` | `180` / `8192` | 调用超时与输出上限 |
| `CACHE_TTL` | `3600` | 缓存生存时间（秒） |
| `MAX_QC_ROUNDS` | `3` | 质检打回最大轮数 |

## 路线图

- [x] 5 Agent 专业 Prompt 体系（三级 JD 拆解 / XYZ 改写 / 五维证据化质检）
- [x] 质检不通过自动回环改写（≤3 轮，轮次对外可见）
- [x] RQ 异步化 + 前端轮询 + 每节点状态落库
- [x] 两种工作流程（优化后测评 / 前后对比测评）与对比数据可视化
- [x] Redis 缓存按模式隔离、异常步骤落库、资源归属鉴权
- [ ] P1：SSE 节点事件推送替代轮询
- [ ] P1：改写环节 LLM stream 输出，前端打字机渲染（不暴露底层 JSON/Prompt）
