# AGENTS.md — 简历多智能体优化助手

## 项目概述
面向求职者的简历优化 Web 工具。输入简历、目标岗位 JD（可选）、个人补充建议（可选），
通过 **LangGraph 编排的 5 个 AI Agent** 对简历做结构化解析、JD 匹配诊断、优化建议、
简历改写，最后经模拟 HR 质检打分，产出诊断报告与优化版简历。

## 技术栈
- **后端**：Python 3.12 / FastAPI / SQLAlchemy / Pydantic-Settings
- **Agent 编排**：LangGraph（并行解析 + 条件循环质检），LLM 走 `coze-coding-dev-sdk`
  （平台托管，`LLMClient`，需平台配额/授权）
- **持久化**：PostgreSQL 16（表 `analysis_records`）+ Redis 7（结果缓存）
- **前端**：Vue 3 + Vite + axios，构建产物由 FastAPI 托管（`frontend/dist`）
- **包管理**：Python 用 `uv`（非打包项目，`[tool.uv] package=false`）；前端用 `pnpm`
- **运行入口**：`backend/app/main.py`（FastAPI）

## 目录结构
```
backend/app/
  main.py          # FastAPI 应用工厂，挂载 API + 托管前端 dist
  config.py        # Settings（env 前缀 RESUME_，读取 backend/.env）
  db.py            # SQLAlchemy engine/session
  models.py        # AnalysisRecord 表模型
  schemas.py       # API 请求/响应模型
  cache.py         # Redis 封装（失败降级为无缓存）
  llm.py           # LLMClient 封装 + ask/ask_json（JSON 解析容错）
  api/routes.py    # /api/health /api/analyze /api/records
  agents/
    state.py       # AgentState（LangGraph 共享状态）
    resume_parser.py  # Agent1 简历解析者
    jd_analyst.py     # Agent2 JD 分析师
    advisor.py        # Agent3 求职简历顾问
    rewriter.py       # Agent4 简历改写员
    hr_qc.py          # Agent5 模拟 HR 质检员
    graph.py          # 图：并行入口 + advisor->rewriter->hr_qc 条件循环
    service.py        # run_analysis：invoke 图 + 持久化 + 缓存
frontend/          # Vue3 + Vite，/api 请求在生产由 FastAPI 同端口提供
scripts/
  build.sh / run.sh   # 预览链路脚本（从 .preview 读端口，绑定 0.0.0.0）
```

## 关键入口 / 核心模块
- LangGraph 图：`backend/app/agents/graph.py`，节点 5 个，质检条件边打回改写员
  （`settings.max_qc_rounds` 控制最大轮数，默认 2）。
- 分析主流程：`backend/app/agents/service.py::run_analysis` + `api/routes.py::analyze`。

## 运行与预览
- 预览链路：`.coze [dev]` → `scripts/build.sh`（uv sync + pnpm build）→
  `scripts/run.sh`（起 redis + postgres，再 `uvicorn app.main:app` 绑定 0.0.0.0:${PORT}）。
- 预览端口：`.preview` 的 `expose_port`（固定 5000），脚本读取，不 hardcode。
- `project_type = "web"`（Vue 自定义栈，非 Next.js 默认模板）；sub_id 不可改。
- 依赖服务：启动需 Redis(6379) 与 PostgreSQL(5432，库 resume_agent / 用户 resume)。

## 用户偏好与长期约束
- 用户技术栈偏好：Python FastAPI + LangGraph + Redis + PostgreSQL + Vue。
- 多 Agent 角色固定 5 个：解析者 / JD分析师 / 简历顾问 / 改写员 / 模拟HR质检。
- 前端走 Vue，不引入 Node/Next.js 后端框架，全部由 Python 承担。

## 常见问题和预防
- **LLM 调用返回"资源点不足"**：这是平台 `coze-coding-dev-sdk` 账户/集成配额问题，
  非本仓库代码缺陷。需在平台升级套餐/配置授权后 LLM 能力才可用；在此之前
  `/api/analyze` 会返回 error 字段，但健康检查、Graph、DB、Redis、前端均正常。
- **uv sync 卡住/失败**：网络慢时用国内镜像
  `uv sync --index-url https://mirrors.aliyun.com/pypi/simple/`；本仓库
  `[tool.uv] package=false`，勿把项目改成 src-layout 打包式。
- 若改了 `frontend/dist` 需重新 `pnpm build`，FastAPI 托管该产物。