import logging
import re
import traceback
from time import time

from aiohttp import ClientSession

logger = logging.getLogger('search.database')

INSERT_SQL = """
INSERT INTO entries (uri, name, src, description, keywords, body) VALUES
 ($1, $2, $3, $4, $5, $6)
"""


def clean(v, limit):
    """
    apparently postgres and asyncpg really don't like 0x00, gives:

    CharacterNotInRepertoireError: invalid byte sequence for encoding "UTF8": 0x00
    """
    v = re.sub('\u0000', '', v)
    if limit and len(v) > limit:
        v = v[:limit]
    return v


DATA_FIELDS = (
    ('uri', 127),
    ('name', 127),
    ('src', 20),
    ('description', None),
    ('keywords', None),
    ('body', None),
)


async def update_index(start, finish, conn, log):
    base_url = 'https://helpmanual.io/search/{:02}.json'
    uris = set()
    repeated = 0

    async with ClientSession() as client:
        try:
            entries = await conn.fetchval('SELECT COUNT(*) from entries')
            log(f'{entries} entries in search database before update')
            log('counting files to process...')
            for i in range(start, finish):
                url = base_url.format(i)
                async with client.head(url) as r:
                    # log(f'{url}: {r.status}')
                    if r.status == 404:
                        finish = i
                        break
            log(f'getting files {start} to {finish}')
            async with conn.transaction():
                start_all = time()
                await conn.execute('DELETE FROM entries')
                for i in range(start, finish):
                    start_file = time()
                    url = base_url.format(i)
                    log(f'processing {url}...')
                    async with client.get(url) as r:
                        r.raise_for_status()
                        data = await r.json()

                    args = []
                    for d in data:
                        uri = d['uri']
                        if uri in uris:
                            repeated += 1
                            continue
                        uris.add(uri)
                        args.append(
                            [clean(d[f], limit) for f, limit in DATA_FIELDS]
                        )
                    await conn.executemany(INSERT_SQL, args)
                    log(f'processed {len(args)} items in {time() - start_file:0.2f}s')
            log(f'finished adding entries, running full vacuum...')
            await conn.execute('VACUUM FULL;')
        except Exception as e:
            trace = ''.join(traceback.format_exc())
            msg = f'error updating index, {e.__class__.__name__}: {e}\n{trace}'
            logger.exception(msg)
            log(msg)
        finally:
            entries = await conn.fetchval('SELECT COUNT(*) from entries')
            log(f'{entries} entries in search database after update, repeated entries {repeated}')
            log(f'total time taken {time() - start_all:0.2f}s')
