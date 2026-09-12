"""一次性重建数据库表结构（开发用）。

执行方式：
    cd projects/backend
    python init_db.py

会 DROP 所有表后重建（清空现有数据，满足 schema 变更需求）。
生产环境请改用 Alembic 迁移。
"""

from app.db import Base, engine
from app.models import AnalysisRecord, Iteration, User  # noqa: F401  # 确保模型被导入


def main() -> None:
    print("Dropping all tables...")
    Base.metadata.drop_all(bind=engine)
    print("Creating all tables...")
    Base.metadata.create_all(bind=engine)
    print("Done. Tables: users, analysis_records, iterations")


if __name__ == "__main__":
    main()
