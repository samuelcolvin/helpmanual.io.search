import json
import re
from urllib.parse import parse_qs

from aiohttp.web_reqrep import json_response

SEARCH_SQL = """\
SELECT url,
       name,
       description,
       ts_rank_cd(vector, q_exact, 16) AS r_exact,
       ts_rank_cd(vector, q_startswith, 16) AS r_startswith
FROM entries,
     to_tsquery(%(exact)s) AS q_exact,
     to_tsquery(%(startswith)s) AS q_startswith
WHERE vector @@ q_startswith
ORDER BY r_exact DESC, r_startswith DESC
LIMIT 20;
"""

SPECIAL = re.compile(r'[&|\n\t]')


def convert_to_search_query(q):
    q = SPECIAL.sub('', q)
    parts = [s for s in q.split(' ') if len(s) > 1]
    return {'exact': ' & '.join(parts), 'startswith': ' & '.join(['{0}:*'.format(s) for s in parts])}


async def index(request):
    data = []
    args = parse_qs(request.query_string)
    query = args.get('query', [None])[0]
    if query:
        async with request.app['pg_pool'].acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(SEARCH_SQL, convert_to_search_query(query))
                async for url, name, description, rank_exact, rank_startswith in cur:
                    data.append({
                        'url': url,
                        'name': name,
                        'descr': description,
                        'rank_exact': rank_exact,
                        'rank_startswith': rank_startswith,
                    })
    return json_response(data)

ARGS_SQL = (
    b"("
    b"%(url)s,"
    b"%(name)s,"
    b"%(description)s,"
    b"create_tsvector(%(name)s, %(description)s, %(body)s)"
    b")"
)

INSERT_ROW_SQL = b'INSERT INTO entries (url, name, description, vector) VALUES '


def chunks(l, n):
    for i in range(0, len(l), n):
        yield l[i:i + n]


async def update(request):
    count = 0
    with open('data.json') as f:
        data = json.load(f)
    from datetime import datetime
    s = datetime.now()
    async with request.app['pg_pool'].acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute('BEGIN;')
            await cur.execute('DELETE FROM entries;')
            for chunk in chunks(data, 1000):
                args = []
                for d in chunk:
                    d['body'] = d['name'] + d['description']
                    v = await cur.mogrify(ARGS_SQL, d)
                    args.append(v)
                    count += 1
                await cur.execute(INSERT_ROW_SQL + b','.join(args))
            await cur.execute('COMMIT;')
    tt = (datetime.now() - s).total_seconds() * 1000
    print('time taken {:0.2f}ms'.format(tt))
    data = {
        'status': 'ok',
        'update_count': count,
        'time_taken': '{:0.2f}ms'.format(tt),
    }
    return json_response(data)
