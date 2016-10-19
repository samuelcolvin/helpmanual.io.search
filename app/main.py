from pathlib import Path

import trafaret as t
from aiohttp import web
from aiopg.pool import _create_pool
from trafaret_config import read_and_validate

from .views import index

THIS_DIR = Path(__file__).parent
BASE_DIR = THIS_DIR.parent
SETTINGS_FILE = BASE_DIR / 'settings.yml'

SETTINGS_STRUCTURE = t.Dict({
    'database': t.Dict({
        'name': t.String,
        'password': t.String,
        t.Key(name='user', default='postgres'): t.String,
        t.Key(name='host', default='localhost'): t.String,
        t.Key(name='port', default=5432): t.Int(gte=0) >> str,
    }),
})


def load_settings() -> dict:
    """
    Read settings.yml and, validation its content.
    :return: settings dict
    """
    settings_file = SETTINGS_FILE.resolve()
    return read_and_validate(str(settings_file), SETTINGS_STRUCTURE)


def pg_dsn(db_settings: dict) -> str:
    """
    :param db_settings: dict of connection settings, see SETTINGS_STRUCTURE for definition
    :return: DSN url suitable for sqlalchemy and aiopg.
    """
    dsn = 'dbname={name} user={user} password={password} host={host} port={port}'
    return dsn.format(**db_settings)


async def startup(app: web.Application):
    app['pg_pool'] = await _create_pool(pg_dsn(app['database']), loop=app.loop)


async def cleanup(app: web.Application):
    app['pg_pool'].close()
    await app['pg_pool'].wait_closed()


def create_app(loop):
    app = web.Application(loop=loop)
    app.update(load_settings())

    app.on_startup.append(startup)
    app.on_cleanup.append(cleanup)

    app.router.add_get('/{name:.*}', index, name='index')
    return app
