from aiohttp.web_reqrep import json_response


async def index(request):
    data = []
    async with request.app['pg_pool'].acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT 1")
            async for row in cur:
                data.append(row)
    return json_response(data)
