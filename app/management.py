import asyncio
import psycopg2
from datetime import datetime
from aiohttp import ClientSession, ClientResponse, FlowControlStreamReader
from aiopg import create_pool

from .main import load_settings, pg_dsn

SETUP_SQL = """
CREATE FUNCTION create_tsvector(name text, description text, keywords text, body text) RETURNS tsvector AS $$
    BEGIN
    RETURN  setweight(to_tsvector(name), 'A')        ||
            setweight(to_tsvector(description), 'B') ||
            setweight(to_tsvector(keywords), 'C') ||
            setweight(to_tsvector(body), 'D');
    END;
$$ LANGUAGE plpgsql;

CREATE TABLE entries (
    uri character varying(63) PRIMARY KEY,
    name character varying(63) NOT NULL,
    src character varying(10) NOT NULL,
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


ARGS_SQL = (
    b"("
    b"%(uri)s,"
    b"%(name)s,"
    b"%(src)s,"
    b"%(description)s,"
    b"create_tsvector(%(name)s, %(description)s, %(keywords)s, %(body)s)"
    b")"
)

INSERT_ROW_SQL = b'INSERT INTO entries (uri, name, src, description, vector) VALUES '


class LongFlowControlStreamReader(FlowControlStreamReader):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._limit = 2 ** 32


class LongClientResponse(ClientResponse):
    flow_control_class = LongFlowControlStreamReader


async def _update_index(loop):
    count = 0
    db_settings = load_settings()['database']
    url_base = 'https://helpmanual.io/search/{:02}.json'

    async with ClientSession(loop=loop, response_class=LongClientResponse) as client:
        async with create_pool(pg_dsn(db_settings), loop=loop) as engine:
            async with engine.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute('BEGIN;')
                    s = datetime.now()
                    try:
                        await cur.execute('DELETE FROM entries;')
                        for i in range(1, 50):
                            url = url_base.format(i)
                            print('downloading {}...'.format(url))
                            async with client.get(url) as r:
                                if r.status == 404:
                                    break
                                r.raise_for_status()
                                data = await r.json()

                            print('saving {} entries to db...'.format(len(data)))
                            args = []
                            for d in data:
                                v = await cur.mogrify(ARGS_SQL, d)
                                args.append(v)
                                count += 1
                            await cur.execute(INSERT_ROW_SQL + b','.join(args))
                            print('{} search indexes stored'.format(count))
                    except:
                        await cur.execute('ROLLBACK;')
                        raise
                    else:
                        await cur.execute('COMMIT;')
                        await cur.execute('VACUUM FULL;')
                    finally:
                        tt = (datetime.now() - s).total_seconds()
                        print('time taken {:0.2f}s'.format(tt))


def update_index():
    loop = asyncio.get_event_loop()
    loop.run_until_complete(_update_index(loop))
    loop.close()
