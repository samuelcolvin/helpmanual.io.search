import asyncio
import psycopg2
from aiopg import create_pool

from .main import load_settings, pg_dsn

SETUP_SQL = """
CREATE FUNCTION create_tsvector(name text, description text, body text) RETURNS tsvector AS $$
    BEGIN
    RETURN  setweight(to_tsvector(name), 'A')        ||
            setweight(to_tsvector(description), 'B') ||
            setweight(to_tsvector(body), 'C');
    END;
$$ LANGUAGE plpgsql;

CREATE TABLE entries (
    url character varying(31) PRIMARY KEY,
    name character varying(31) NOT NULL,
    vector tsvector NOT NULL,
    description text
);

CREATE INDEX vector_index ON entries USING GIN (vector);
"""


async def create_tables(db_settings):
    async with create_pool(pg_dsn(db_settings)) as engine:
        async with engine.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(SETUP_SQL)


def prepare_database(delete_existing: bool) -> bool:
    """
    (Re)create a fresh database and run migrations.

    :param delete_existing: whether or not to drop an existing database if it exists
    :return: whether or not a database as (re)created
    """
    db = load_settings()['database']

    conn = psycopg2.connect(
        password=db['password'],
        host=db['host'],
        port=db['port'],
        user=db['user'],
    )
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute('SELECT EXISTS (SELECT datname FROM pg_catalog.pg_database WHERE datname=%s)', (db['name'],))
    already_exists = bool(cur.fetchone()[0])
    if already_exists:
        if not delete_existing:
            print('database "{name}" already exists, skipping'.format(**db))
            return False
        else:
            print('dropping database "{name}" as it already exists...'.format(**db))
            cur.execute('DROP DATABASE {name}'.format(**db))
    else:
        print('database "{name}" does not yet exist'.format(**db))

    print('creating database "{name}"...'.format(**db))
    cur.execute('CREATE DATABASE {name}'.format(**db))
    cur.close()
    conn.close()

    loop = asyncio.get_event_loop()
    loop.run_until_complete(create_tables(db))
    return True
