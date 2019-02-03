#!/usr/bin/env python3
import asyncio
import logging

import asyncpg
import click
import uvloop
from aiohttp.web import run_app

from app.database import prepare_database as _prepare_database
from app.logs import setup_logging
from app.main import Settings, create_app
from app.update import update_index as _update_index

logger = logging.getLogger('search.run')


@click.group()
@click.pass_context
def cli(ctx):
    """
    Run helpmanual search
    """
    pass


@cli.command()
def web():
    """
    Serve the application. If the database doesn't already exist it will be created.
    """
    settings = Settings()
    setup_logging()
    logger.info('settings: %s', settings.to_string(pretty=True))

    asyncio.get_event_loop().close()
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    loop = asyncio.get_event_loop()
    loop.run_until_complete(_prepare_database(settings))
    logger.info('starting server...')
    app = create_app(settings)
    run_app(app, port=8000, print=lambda v: None, access_log=None)


@cli.command()
@click.option('--force', is_flag=True)
def reset_db(force):
    setup_logging()
    settings = Settings()
    logger.info('settings: %s', settings.to_string(pretty=True))
    loop = asyncio.get_event_loop()
    logger.info('running prepare_database, force: %r...', force)
    loop.run_until_complete(_prepare_database(settings, force))


async def __update_index(start, finish):
    settings = Settings()
    pool = await asyncpg.create_pool(dsn=settings.dsn)

    async def log(msg):
        print(msg)

    await _update_index(start, finish, pool, log)

    await pool.close()


@cli.command()
@click.option('--start', type=int, default=1)
@click.option('--finish', type=int, default=200)
def update_index(start, finish):
    asyncio.get_event_loop().close()
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    loop = asyncio.get_event_loop()
    loop.run_until_complete(__update_index(start, finish))


if __name__ == '__main__':
    cli()
