"""Windows 兼容的 RQ Worker 启动脚本。

Windows 不支持 os.fork，需使用 SimpleWorker（同进程执行 job）。
"""

from redis import Redis
from rq.worker import SimpleWorker

from app.config import get_settings

settings = get_settings()


def main() -> None:
    # RQ 内部期望 bytes，不能 decode_responses=True
    conn = Redis.from_url(settings.redis_url, decode_responses=False)
    worker = SimpleWorker(["resume"], connection=conn)
    print(f"RQ SimpleWorker 启动，监听队列: resume")
    print(f"Redis URL: {settings.redis_url}")
    print(f"PID: {worker.pid}")
    print("-" * 40)
    worker.work(with_scheduler=False)


if __name__ == "__main__":
    main()
