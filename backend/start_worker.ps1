# RQ Worker 启动脚本（PowerShell）
# 用法：在 projects/backend 目录下执行 .\start_worker.ps1
# 消费 "resume" 队列，执行首轮/迭代轮流水线任务

$ErrorActionPreference = "Stop"

# 激活 venv
$venvActivate = "..\.venv\Scripts\Activate.ps1"
if (Test-Path $venvActivate) {
    . $venvActivate
} else {
    Write-Error "未找到 .venv，请先创建虚拟环境"
    exit 1
}

# 复用 backend/.env 的 RESUME_REDIS_URL
$envFile = ".env"
if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        if ($_ -match '^\s*RESUME_REDIS_URL\s*=\s*(.+)$') {
            $env:RESUME_REDIS_URL = $matches[1].Trim()
        }
    }
}
if (-not $env:RESUME_REDIS_URL) {
    $env:RESUME_REDIS_URL = "redis://127.0.0.1:6379/0"
}

Write-Host "启动 RQ Worker，消费队列: resume"
Write-Host "Redis URL: $env:RESUME_REDIS_URL"
Write-Host "工作目录: $(Get-Location)"
Write-Host "按 Ctrl+C 停止"
Write-Host "-----------------------------------"

rq worker resume --url $env:RESUME_REDIS_URL
