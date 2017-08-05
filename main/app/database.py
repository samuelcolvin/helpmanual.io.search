import logging

import asyncpg

from .main import Settings

DB_EXISTS = 'SELECT EXISTS (SELECT datname FROM pg_catalog.pg_database WHERE datname=$1)'

logger = logging.getLogger('search.database')


async def prepare_database(settings: Settings, overwrite_existing: bool=False) -> bool:
    """
    (Re)create a fresh database and run migrations.

    :param overwrite_existing: whether or not to drop an existing database if it exists
    :return: whether or not a database has been (re)created
    """
    no_db_dsn, _ = settings.dsn.rsplit('/', 1)

    conn = await asyncpg.connect(dsn=no_db_dsn)
    try:
        db_exists = await conn.fetchval(DB_EXISTS, settings.db_name)
        if db_exists:
            if not overwrite_existing:
                logger.info('database "%s" already exists, skipping setup', settings.db_name)
                return False
            else:
                logger.info('database "%s" already exists...', settings.db_name)
        else:
            logger.info('database "%s" does not yet exist', settings.db_name)
            logger.info('creating database "%s"...', settings.db_name)
            await conn.execute('CREATE DATABASE {}'.format(settings.db_name))
        logger.info('settings db timezone to utc...')
        await conn.execute("ALTER DATABASE {} SET TIMEZONE TO 'UTC';".format(settings.db_name))
    finally:
        await conn.close()

    conn = await asyncpg.connect(dsn=settings.dsn)
    try:
        logger.info('creating tables from model definition...')
        await conn.execute(settings.models_sql)
    finally:
        await conn.close()
    return True
