from urllib.parse import parse_qs
from aiohttp.web_reqrep import json_response

SEARCH_SQL = """\
SELECT url, name, description, ts_rank_cd(vector, query) AS rank
FROM entries, to_tsquery(%s) AS query
WHERE vector @@ query
ORDER BY rank DESC
LIMIT 20;
"""


async def index(request):
    data = []
    args = parse_qs(request.query_string)
    query = args.get('query', [None])[0]
    if query:
        async with request.app['pg_pool'].acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(SEARCH_SQL, (query,))
                async for url, name, description, _ in cur:
                    data.append({
                        'url': url,
                        'name': name,
                        'descr': description,
                    })
    return json_response(data)

ARGS_SQL = """(
    %(url)s,
    %(name)s,
    %(description)s,
    setweight(to_tsvector(%(name)s), 'A')        ||
    setweight(to_tsvector(%(description)s), 'B') ||
    setweight(to_tsvector(%(body)s), 'C')
)
"""

INSERT_ROW_SQL = 'INSERT INTO entries (url, name, description, vector) VALUES '

DATA = [
    {'url': '/frank/', 'name': 'frank', 'description': 'first man', 'body': 'blah apple'},
    {'url': '/fred/', 'name': 'fred', 'description': 'whatever', 'body': 'bang frank'},
    {'url': '/anna/', 'name': 'anne', 'description': 'wherever', 'body': 'boom whatever'},
]

async def update(request):
    count = 0
    async with request.app['pg_pool'].acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute('BEGIN;')
            await cur.execute('DELETE FROM entries;')
            args = []
            for d in DATA:
                v = await cur.mogrify(ARGS_SQL, d)
                args.append(v.decode())
                count += 1
            await cur.execute(INSERT_ROW_SQL + ','.join(args))
            await cur.execute('COMMIT;')
    data = {
        'status': 'ok',
        'update_count': count,
    }
    return json_response(data)
