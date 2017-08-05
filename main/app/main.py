import asyncio
from pathlib import Path

import asyncpg
from aiohttp import web
from pydantic import DSN, BaseSettings

from .views import index

THIS_DIR = Path(__file__).parent


class Settings(BaseSettings):
    db_name = 'helpmanual'
    db_user = 'postgres'
    db_password: str = None
    db_host = 'localhost'
    db_port = '5432'
    db_driver = 'postgres'
    db_query: dict = None
    dsn: DSN = None
    models_sql = (THIS_DIR / 'models.sql').read_text()


async def startup(app: web.Application):
    settings: Settings = app['settings']
    loop = app.loop or asyncio.get_event_loop()
    app.update(
        db=await asyncpg.create_pool(dsn=settings.dsn, loop=loop),
    )


async def cleanup(app: web.Application):
    await app['db'].close()


def create_app(settings: Settings=None):
    settings = settings or Settings()
    app = web.Application()
    app.update(
        settings=settings
    )

    app.on_startup.append(startup)
    app.on_cleanup.append(cleanup)

    app.router.add_get('/{q:.*}', index, name='index')
    return app
