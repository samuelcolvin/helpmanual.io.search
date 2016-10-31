import re

from aiohttp.web_reqrep import json_response

EXACT_MATCH_SQL = """\
SELECT uri,
       name,
       src,
       description
FROM entries
WHERE name = %s
LIMIT 5;
"""

SEARCH_SQL = """\
SELECT uri,
       name,
       src,
       description,
       ts_rank_cd(vector, q_exact, 16) AS r_exact,
       ts_rank_cd(vector, q_startswith, 16) AS r_startswith
FROM entries,
     to_tsquery(%(q_exact)s) AS q_exact,
     to_tsquery(%(q_startswith)s) AS q_startswith
WHERE vector @@ q_startswith AND name != %(exclude)s
ORDER BY r_exact DESC, r_startswith DESC
LIMIT 12;
"""

SPECIAL = re.compile(r'[&|\n\t\(\)]')


def convert_to_search_query(base, exclude):
    q = SPECIAL.sub('', base)
    parts = [s for s in q.split(' ') if len(s) > 1]
    return {
        'exclude': exclude,
        'q_exact': ' & '.join(parts),
        'q_startswith': ' & '.join(['{0}:*'.format(s) for s in parts])
    }


ALLOWED_ORIGINS = {
    'https://helpmanual.io',
    'http://localhost:8000',
}
MAX_DESCRIPTION_LENGTH = 120


def shorten_description(d):
    if len(d) > MAX_DESCRIPTION_LENGTH:
        d = d[:MAX_DESCRIPTION_LENGTH - 3] + '...'
    return d


async def index(request):
    data = []
    exclude = '_'
    query = request.match_info['name']
    if query:
        async with request.app['pg_pool'].acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(EXACT_MATCH_SQL, (query[:50],))
                async for uri, name, src, description in cur:
                    data.append({
                        'uri': uri,
                        'name': name,
                        'src': src,
                        'description': shorten_description(description),
                    })
                    exclude = name

                await cur.execute(SEARCH_SQL, convert_to_search_query(query, exclude))
                async for uri, name, src, description, *_ in cur:
                    data.append({
                        'uri': uri,
                        'name': name,
                        'src': src,
                        'description': shorten_description(description),
                    })
    headers = None
    origin = request.headers.get('origin')
    if origin in ALLOWED_ORIGINS:
        headers = {'Access-Control-Allow-Origin': origin}
    return json_response(data, headers=headers)
