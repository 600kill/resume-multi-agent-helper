# 简历多智能体优化助手

输入简历原文、目标岗位 JD 和个人诉求，由 **LangGraph 编排的 5 个 AI Agent** 自动完成
「解析 → 岗位分析 → 优化建议 → 简历改写 → HR 质检」，质检不达标会带着具体修改意见**自动打回改写、最多迭代 3 轮**，
最终产出量化评分报告与岗位定制版简历。

- 后端：Python · FastAPI · LangGraph · PostgreSQL · Redis
- 前端：Vue 3 · Vite · Axios（构建产物由 FastAPI 同端口托管）
- LLM：OpenAI 兼容接口（当前接入 `glm-4.6v`，经本地 CC Switch / Codex 客户端转发），换模型只改配置

## 实际运行截图

**① 首页：填写简历 + JD，右上角实时健康检查显示「服务在线」**

![首页](docs/images/01-home.png)

**② 提交后：5 Agent 流水线实时进度（解析 / JD 分析并行 → 顾问 → 改写 → HR 质检循环）**

![执行中](docs/images/02-running.png)

**③ 分析报告：HR 五维评分、JD 关键词匹配、逐条优化建议**

![分析报告](docs/images/03-report.png)

**④ 优化后简历：面向目标岗位重写，量化成果前置（STAR 结构、Markdown 正文）**

![优化后简历](docs/images/05-rewritten.png)

**⑤ 自动生成的 OpenAPI 接口文档（`/docs`）**

![API 文档](docs/images/04-api-docs.png)

## 多 Agent 流水线

```
                 ┌──────────────────┐
START ──────────▶│ ① 简历解析者     │──┐
                 └──────────────────┘  │
                                       ├─▶ ③ 求职简历顾问 ─▶ ④ 简历改写员 ─▶ ⑤ HR 质检员
                 ┌──────────────────┐  │                                      │
                 │ ② JD 分析师      │──┘                                      │
                 └──────────────────┘                                          │
                   ◀──────────── 质检不通过：携带 fix_instructions 打回（≤3 轮）◀┘
                                                       │ 合格 / 达 3 轮上限
                                                       ▼
                                                      END
```

| Agent | 输入 | 产出 |
|---|---|---|
| ① 简历解析者 | 简历原文 | 基本信息/教育/经历/项目/技能等结构化 JSON |
| ② JD 分析师 | JD 文本（与①并行） | 硬性要求、优先要求、筛选关键词、加分项 |
| ③ 求职简历顾问 | ① + ② + 用户诉求 | 差距诊断、关键词缺口、逐条可执行优化建议 |
| ④ 简历改写员 | 原文 + JD 分析 + 顾问建议（+ 上轮质检意见） | 岗位定制版完整简历（STAR 化、量化表达） |
| ⑤ 模拟 HR 质检员 | 改写稿 + JD | 五维评分、是否通过、`fix_instructions` 修改清单 |

**质检回环**：⑤ 不通过时把具体修改意见写入状态打回 ④，改写员在下一轮 prompt 中逐条落实，
HR 复核时对照上轮意见验收；达到 3 轮上限自动结束并返回最后一稿，防止死循环。

## 技术栈与目录

```
projects/
├─ backend/
│  ├─ app/
│  │  ├─ main.py              # FastAPI 入口，同端口托管前端 dist
│  │  ├─ config.py            # 全部配置（RESUME_ 前缀环境变量）
│  │  ├─ llm.py               # LLM 封装：仅暴露 ask / ask_json，换模型只改这里
│  │  ├─ cache.py             # Redis：统一 key 工具 + HIT/MISS 日志 + TTL
│  │  ├─ db.py / models.py    # SQLAlchemy + PostgreSQL（analysis_records 表）
│  │  ├─ api/routes.py        # /api/health /api/analyze /api/records
│  │  └─ agents/              # 5 个 Agent + state.py + graph.py + service.py
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

表结构由 SQLAlchemy 在服务启动时自动创建（`analysis_records`），无需手动建表。

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

### 4. 启动并访问

```powershell
cd backend
..\.venv\Scripts\uvicorn.exe app.main:app --host 127.0.0.1 --port 5000
```

- 应用首页：http://127.0.0.1:5000
- 接口文档：http://127.0.0.1:5000/docs

## HTTP 接口

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/health` | 服务健康检查（前端右上角状态灯） |
| POST | `/api/analyze` | 提交简历/JD，同步执行完整流水线，返回全部 Agent 结果 |
| GET | `/api/records` | 历史分析记录列表（状态、岗位、评分、时间） |
| GET | `/api/records/{record_id}` | 查询单条分析记录详情（含五份 Agent 结果） |

`POST /api/analyze` 为同步接口，5 Agent + 质检迭代约需 2–5 分钟，前端超时已设为 10 分钟。

## 工程要点

**Redis 结果缓存（主流程）**

- 统一 key：`resume:v1:analysis:{sha256}`，哈希内容为四项输入（简历/JD/诉求/岗位）按 key 排序后的 JSON；
  参数顺序不影响命中，版本段 `v1` 便于结构升级时让旧缓存自然失效。
- TTL 3600 秒；命中/未命中均写日志：`cache HIT/MISS key=... meta={record_id, target_position}`。
- 同内容重复提交直接返回缓存结果（秒级），但仍会新建一条历史记录；Redis 不可用时自动降级为无缓存，不阻断服务。

**PostgreSQL 持久化**：每次分析落库 `analysis_records`（状态 running/done/error、五份 Agent 结果、质检轮次、错误信息）。

**质检迭代**：`AgentState` 携带 `fix_instructions` 与 `iteration_round`，最大 3 轮（`RESUME_MAX_QC_ROUNDS` 可调）。

## 实测记录（2026-09-11）

- 环境：Windows + Docker（PostgreSQL 16.15 / Redis 7，均 healthy），uvicorn 单进程，glm-4.6v
- 真实简历端到端（数据分析实习生岗）：5 Agent 全部产出，HR 五维评分 85/90/90/90/95、总分 89，首轮通过，耗时 202 秒
- 同内容二次提交（记录 #9 → #10）：日志输出 `cache HIT key=resume:v1:analysis:8932… meta={'record_id': 10, ...}`，秒级返回、不再调用 LLM，截图即该次命中结果
- 缓存未命中、质检 3 轮上限、修改意见逐轮传递：通过确定性脚本验证（mock LLM + 真实 PG/Redis）

## 配置项一览（均带 `RESUME_` 前缀，见 `backend/app/config.py`）

| 配置 | 默认值 | 说明 |
|---|---|---|
| `DATABASE_URL` | `postgresql://resume:resume@127.0.0.1:5432/resume_agent` | PostgreSQL 连接串 |
| `REDIS_URL` | `redis://127.0.0.1:6379/0` | Redis 连接串 |
| `MODEL` | `glm-4.6v` | LLM 模型名 |
| `LLM_BASE_URL` | `http://127.0.0.1:15721/v1` | OpenAI 兼容端点 |
| `LLM_API_KEY` | `ccswitch-local` | API Key（本地代理占位即可） |
| `LLM_TIMEOUT` / `LLM_MAX_TOKENS` | `180` / `8192` | 调用超时与输出上限 |
| `CACHE_TTL` | `3600` | 缓存生存时间（秒） |
| `MAX_QC_ROUNDS` | `3` | 质检打回最大轮数 |
