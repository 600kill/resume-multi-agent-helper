# 简历多智能体优化助手

面向求职者的简历优化 Web 工具。输入简历、目标岗位 JD（可选）和个人补充建议（可选），
通过 **LangGraph 编排的 5 个 AI Agent** 依次完成解析、诊断、建议、改写、质检，
产出诊断报告与优化版简历。

## 多 Agent 流水线

| Agent | 职责 |
|---|---|
| ① 简历解析者 | 结构化提取简历关键信息（教育/经历/项目/技能） |
| ② JD 分析师 | 拆解岗位 JD，提炼硬性要求、技术栈、筛选关键词 |
| ③ 求职简历顾问 | 结合简历 + JD + 用户建议，诊断差距并给出优化建议 |
| ④ 简历改写员 | 按建议产出面向目标岗位的优化版简历（STAR 化） |
| ⑤ 模拟 HR 质检员 | 多维打分与质检，未通过则打回改写员迭代 |

质检不通过会打回 Step ④ 迭代，最多迭代 `max_qc_rounds`（默认 2）轮。

## 快速开始

```bash
# 1. 依赖服务：Redis + PostgreSQL（库 resume_agent / 用户 resume / 密码 resume）
redis-server &
service postgresql start

# 2. 安装依赖并构建前端
uv sync --index-url https://mirrors.aliyun.com/pypi/simple/
cd frontend && pnpm install && pnpm build && cd ..

# 3. 启动
cd backend && ../.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 5000
```

访问 `http://localhost:5000`，接口文档见 `/docs`。

## 环境变量（前缀 `RESUME_`）
- `RESUME_DATABASE_URL`：PostgreSQL 连接串，默认 `postgresql://resume:resume@127.0.0.1:5432/resume_agent`
- `RESUME_REDIS_URL`：Redis 连接串，默认 `redis://127.0.0.1:6379/0`
- `RESUME_MODEL`：LLM 模型，默认 `doubao-seed-2-0-pro-260215`

## 说明
- LLM 依赖平台 `coze-coding-dev-sdk` 授权与配额；配额不足时 `/api/analyze`
  会返回 error 字段，但健康检查、Graph、DB、Redis、前端均正常。