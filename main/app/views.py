import logging
import re
from datetime import datetime

from aiohttp.web import HTTPUnauthorized, Response, StreamResponse

from .update import update_index

logger = logging.getLogger('search.views')

EXACT_MATCH_SQL = """\
SELECT array_to_json(array_agg(row_to_json(t)))
FROM (
  SELECT uri, name, src, left(description, 120) AS description
  FROM entries
  WHERE name = $1
  LIMIT 5
) t;
"""

SEARCH_SQL = """\
SELECT array_to_json(array_agg(row_to_json(t)))
FROM (
  SELECT v.uri, v.name, v.src, left(v.description, 120) AS description
  FROM (
    SELECT uri, name, src, description,
           ts_rank_cd(vector, q_exact, 16) AS r_exact,
           ts_rank_cd(vector, q_startswith, 16) AS r_startswith
    FROM entries,
         to_tsquery($1) AS q_exact,
         to_tsquery($2) AS q_startswith
    WHERE vector @@ q_startswith AND name != $3
    ORDER BY r_exact DESC, r_startswith DESC
    LIMIT 12
  ) v
) t;
"""

SPECIAL = re.compile(r'[&|\n\t\(\)]')


def convert_to_search_query(base, exclude):
    q = SPECIAL.sub('', base)
    parts = [s for s in q.split(' ') if len(s) > 1]
    return (
        ' & '.join(parts),
        ' & '.join([f'{s}:*' for s in parts]),
        exclude,
    )


ALLOWED_ORIGINS = 'https://helpmanual.io', 'http://localhost:8000'


async def search(request):
    data = '[]'
    exclude = '_'
    query = request.match_info['q']
    if query:
        async with request.app['db'].acquire() as conn:
            name = query[:50]
            data1 = await conn.fetchval(EXACT_MATCH_SQL, name)
            if data1:
                exclude = name

            args = convert_to_search_query(query, exclude)
            data2 = await conn.fetchval(SEARCH_SQL, *args)

        if data1 and data2:
            data = data1[:-1] + ',' + data2[1:]
        else:
            data = data1 or data2 or data

    headers = {}
    origin = request.headers.get('origin')
    if origin in ALLOWED_ORIGINS:
        headers = {'Access-Control-Allow-Origin': origin}
    return Response(text=data, content_type='application/json', headers=headers)


STREAM_HEAD = b"""\
<!DOCTYPE html>
<title>helpmanual search update</title>
<style>
  html {font-family: monospace; white-space: pre-wrap; margin: 0 50px 80px;} 
  body {margin: 0}
  h1 {margin: 0}
</style>
<h1>helpmanual search update</h1>
<script>
  var auto_scroll = true
  setInterval(function(){
    auto_scroll && window.scrollTo(0,document.body.scrollHeight)
    document.body.style.backgroundColor = auto_scroll ? "white" : "#e8e8e8";
  }, 50)
</script>
<body onclick="auto_scroll = !auto_scroll">"""


async def update(request):
    if request.match_info['token'] != request.app['settings'].update_token:
        raise HTTPUnauthorized(text='invalid token')
    r = StreamResponse()
    r.content_type = 'text/html'
    await r.prepare(request)
    r.write(STREAM_HEAD)

    def log(msg):
        msg_ = f'{datetime.now():%H:%M:%S} &gt; {msg}'
        logger.info(msg)
        r.write((msg_ + '\n').encode())

    start, finish = int(request.match_info['start']), int(request.match_info['finish'])
    async with request.app['db'].acquire() as conn:
        await update_index(start, finish, conn, log)
    return r
