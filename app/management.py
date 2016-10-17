import asyncio
import psycopg2
from aiopg import create_pool

from .main import load_settings, pg_dsn

CREATE_TABLES_SQL = """
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
                await cur.execute(CREATE_TABLES_SQL)


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


VECTOR_SQL = """
setweight(to_tsvector(%(name)s), 'A')        ||
setweight(to_tsvector(%(description)s), 'B') ||
setweight(to_tsvector(%(body)s), 'C')
"""

INSERT_ROW_SQL = """
INSERT INTO entries (url, name, description, vector) VALUES(
    %(url)s,
    %(name)s,
    %(description)s,
    {0}
)
ON CONFLICT (path) DO UPDATE SET
  url = %(url)s,
  description = %(description)s,
  vector = {0};
""".format(VECTOR_SQL)

SEARCH_SQL = """\
SELECT name, description, url, ts_rank_cd(vector, query) AS rank
FROM entries, to_tsquery(%s) AS query
WHERE vector @@ query
ORDER BY rank DESC
LIMIT 20;
"""

async def _populate_dummy_data(db_settings):
    async with create_pool(pg_dsn(db_settings)) as engine:
        async with engine.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(INSERT_ROW_SQL, dict(path='foo', name='bar', url='/', description='x', body='boom'))
                await cur.execute(INSERT_ROW_SQL, dict(path='a', name='b', url='/', description='c', body='d'))


def populate_dummy_db():
    db = load_settings()['database']

    loop = asyncio.get_event_loop()
    loop.run_until_complete(_populate_dummy_data(db))
    return True
