"""
demo/seed_user_003.py

测试账户 003 的数据注入脚本。直接写入 PostgreSQL，绕过 Gateway API。

【环境变量依赖】
运行前请确保项目根目录下的 .env 文件配置了以下 PostgreSQL 连接参数：
    PG_HOST     数据库地址（本地填 127.0.0.1，云端填 RDS 公网 IP）
    PG_PORT     数据库端口（默认 5432）
    PG_USER     数据库用户名
    PG_PASSWORD 数据库密码
    PG_DB       数据库名称

Usage: python demo/seed_user_003.py
"""

import asyncio
import sys

sys.path.insert(0, ".")

from alert_db.session import AsyncSessionLocal


async def seed() -> None:
    """注入 user_003 的测试数据。"""
    async with AsyncSessionLocal() as session:
        print("Seeding data for user_003...")

        # TODO: 在此处添加 user_003 的测试数据

        print("\n✅ Seed complete for user_003")


if __name__ == "__main__":
    asyncio.run(seed())
