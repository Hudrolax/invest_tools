import asyncpg
import asyncio
from config import DB_HOST, DB_USER, DB_PASS, DB_NAME


async def drop_test_databases(host, user, password, db_name, db_prefix):
    conn = await asyncpg.connect(host=host, user=user, password=password, database=db_name)
    # получаем список всех баз данных
    dbs = await conn.fetch("SELECT datname FROM pg_database WHERE datistemplate = false;")
    # перебираем базы данных
    for db in dbs:
        if db['datname'].startswith(db_prefix):
            # отключаем все подключения к этой базе данных
            await conn.execute(f"SELECT pg_terminate_backend(pg_stat_activity.pid) FROM pg_stat_activity WHERE pg_stat_activity.datname = '{db['datname']}' AND pid <> pg_backend_pid();")
            # удаляем базу данных
            await conn.execute(f"DROP DATABASE IF EXISTS {db['datname']};")
    await conn.close()

if __name__ == '__main__':
    asyncio.run(drop_test_databases(DB_HOST, DB_USER, DB_PASS, DB_NAME, 'test_db_'))