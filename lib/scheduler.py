'''
Simple scheduler implementation
'''
import asyncio
import logging
from time import time
from typing import Any, Optional

import asyncpg

from lib.db import pool
from lib.checker import check_url

_logger = logging.getLogger(__name__)


async def main_loop(config: dict[str, Any]):
    '''
    Scheduler main loop routine
    '''
    interval = float(config['scheduler']['interval'])
    semaphore = asyncio.Semaphore(int(config['scheduler']['max_concurrency']))
    background_tasks = set()

    async with pool.acquire() as conn:
        watchlist_fetch = await conn.prepare(
            # NOTE: fields must match execute() parameters
            'SELECT id, url, content_rx, "interval" + EXTRACT(EPOCH FROM last_start) run_at '
            'FROM watchlist '
            'WHERE enabled '
            # pick never ran...
            'AND ((last_start IS NULL AND last_end IS NULL) '
            # ...or to be run within current scheduler tick
            'OR (last_start < to_timestamp($1 - "interval"))) '
            # NULLS FIRST makes sure never executed tasks will run first
            'ORDER BY 4 NULLS FIRST'
        )

        while True:
            tick_start = time()
            record: asyncpg.Record
            async for record in watchlist_fetch.cursor(tick_start + interval):
                task = asyncio.create_task(_execute(semaphore, **dict(record.items())))
                # a workaround for https://github.com/python/cpython/issues/88831
                background_tasks.add(task)
                task.add_done_callback(background_tasks.discard)

            tick_elapsed = time() - tick_start

            if tick_elapsed < interval:
                await asyncio.sleep(interval - tick_elapsed)

            if tick_elapsed > interval:
                _logger.warning(
                    'Performance problem: iteration time exceeded by %fs', tick_elapsed - interval
                )


async def _execute(semaphore: asyncio.Semaphore,
                   id: int, url: str, content_rx: Optional[str] = None, # pylint:disable=W0622
                   run_at: Optional[int] = None):
    '''
    Task coroutine.
    Mass created from main loop and controlled by semaphore
    '''
    async with semaphore:
        start_time = time()
        if run_at and run_at > start_time:
            delta = run_at - start_time

            await asyncio.sleep(delta)
            start_time = run_at

        result = await check_url(url, content_rx)

        end_time = time()

        async with pool.acquire() as conn:
            # log check results
            await conn.execute(
                'INSERT INTO check_log (wl_id, start, end, connect, ttfb, response, '
                'status_code, content_check, error_message) '
                'VALUES ($1, to_timestamp($2), to_timestamp($3), $4, $5, $6, $7, $8, $9)',
                id, start_time, end_time, result.connection, result.ttfb, result.response,
                result.status_code, result.error_message
            )
            # update scheduler fields
            await conn.execute(
                'UPDATE watchlist '
                'SET last_start = to_timestamp($1), last_end = to_timestamp($2) '
                'WHERE id = $3',
                start_time, end_time, id
            )
