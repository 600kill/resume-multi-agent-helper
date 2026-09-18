"""为 analysis_records 表添加 P0 新字段（幂等 ALTER TABLE）。"""

from sqlalchemy import text

from .db import SessionLocal

MIGRATIONS = [
    "ALTER TABLE analysis_records ADD COLUMN IF NOT EXISTS current_step_name VARCHAR(64)",
    "ALTER TABLE analysis_records ADD COLUMN IF NOT EXISTS current_step_desc TEXT",
    "ALTER TABLE analysis_records ADD COLUMN IF NOT EXISTS iteration_round INTEGER DEFAULT 0",
    "ALTER TABLE analysis_records ADD COLUMN IF NOT EXISTS failed_step VARCHAR(64)",
    "ALTER TABLE analysis_records ADD COLUMN IF NOT EXISTS cache_hit BOOLEAN DEFAULT FALSE",
    # 两种工作流程：optimize=直接优化后测评；compare=原始测评→优化→再测评
    "ALTER TABLE analysis_records ADD COLUMN IF NOT EXISTS mode VARCHAR(16) DEFAULT 'optimize'",
    "ALTER TABLE analysis_records ADD COLUMN IF NOT EXISTS baseline_qc JSON",
]


def run_migrations() -> None:
    db = SessionLocal()
    try:
        for sql in MIGRATIONS:
            try:
                db.execute(text(sql))
                print(f"OK: {sql[:80]}")
            except Exception as e:
                print(f"SKIP: {e}")
        db.commit()
        print("migrations done")
    finally:
        db.close()


if __name__ == "__main__":
    run_migrations()
