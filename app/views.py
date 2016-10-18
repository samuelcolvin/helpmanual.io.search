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
LIMIT 20;
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


async def index(request):
    data = []
    args = parse_qs(request.query_string)
    query = args.get('query', [None])[0]
    if query:
        async with request.app['pg_pool'].acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(SEARCH_SQL, convert_to_search_query(query))
                async for uri, name, description, exact_match, rank_exact, rank_startswith in cur:
                    data.append({
                        'uri': uri,
                        'name': name,
                        'descr': description,
                        'exact_match': exact_match,
                        'rank_exact': rank_exact,
                        'rank_startswith': rank_startswith,
                    })
    return json_response(data)
