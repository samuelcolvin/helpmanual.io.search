import logging
import traceback
from time import time

from aiohttp import ClientSession

logger = logging.getLogger('search.database')

INSERT_SQL = """
INSERT INTO entries (uri, name, src, description, keywords, body) VALUES
 ($1, $2, $3, $4, $5, $6)
"""


async def update_index(start, finish, conn, log):
    base_url = 'https://helpmanual.io/search/{:02}.json'

    async with ClientSession() as client:
        try:
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
                await conn.execute('DELETE FROM entries;')
                for i in range(start, finish):
                    start_file = time()
                    url = base_url.format(i)
                    log(f'downloading {url}...')
                    async with client.get(url) as r:
                        r.raise_for_status()
                        data = await r.json()

                    log(f'saving {len(data)} entries to db...')
                    args = []
                    for d in data:
                        args.append((
                            d['uri'],
                            d['name'],
                            d['src'],
                            d['description'],
                            d['keywords'],
                            d['body'],
                        ))
                    await conn.executemany(INSERT_SQL, args)
                    log(f'{url} processed {len(args)} items in {time() - start_file:0.2f}s')
        except Exception as e:
            trace = ''.join(traceback.format_exc())
            msg = f'error updating index, {e.__class__.__name__}: {e}\n{trace}'
            logger.exception(msg)
            log(msg)
        else:
            await conn.execute('VACUUM FULL;')
        finally:
            log(f'total time taken {time() - start_all:0.2f}s')
