import re
from urllib.parse import parse_qs

from aiohttp.web_reqrep import json_response

SEARCH_SQL = """\
SELECT uri,
       name,
       description,
       name = %(name)s as name_exact,
       ts_rank_cd(vector, q_exact, 16) AS r_exact,
       ts_rank_cd(vector, q_startswith, 16) AS r_startswith
FROM entries,
     to_tsquery(%(q_exact)s) AS q_exact,
     to_tsquery(%(q_startswith)s) AS q_startswith
WHERE vector @@ q_startswith
ORDER BY name_exact DESC, r_exact DESC, r_startswith DESC
LIMIT 12;
"""

SPECIAL = re.compile(r'[&|\n\t]')


def convert_to_search_query(base):
    q = SPECIAL.sub('', base)
    parts = [s for s in q.split(' ') if len(s) > 1]
    return {
        'name': base,
        'q_exact': ' & '.join(parts),
        'q_startswith': ' & '.join(['{0}:*'.format(s) for s in parts])
    }


ALLOWED_ORIGINS = {
    'https://helpmanual.io',
    'http://localhost:8000',
}


async def index(request):
    data = []
    args = parse_qs(request.query_string)
    query = args.get('query', [None])[0]
    if query:
        async with request.app['pg_pool'].acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(SEARCH_SQL, convert_to_search_query(query))
                async for uri, name, description, *_ in cur:
                    data.append({
                        'uri': uri,
                        'name': name,
                        'descr': description,
                    })
    headers = None
    origin = request.headers.get('origin')
    if origin in ALLOWED_ORIGINS:
        headers = {'Access-Control-Allow-Origin': origin}
    return json_response(data, headers=headers)
