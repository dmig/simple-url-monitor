'''
Testing fixtures
'''

from contextlib import contextmanager
from pathlib import Path
from random import randrange
from threading import Thread

import pytest
import pytest_asyncio
from tests.lib.http_server import DelayingHTTPServer
from lib.config import load_config
from lib.db import get_pool, initialize_pool

# pylint:disable=C0115,C0116
@pytest.fixture
def http_server():
    @contextmanager
    def server(ttfb=0, response=0):
        """Delaying HTTP Server fixture

        Args:
            ttfb (int, optional): Time To First Byte delay, in milliseconds. Defaults to 0.
            response (int, optional): Response delay, in milliseconds. Defaults to 0.

        Yields:
            int: server port number
        """
        while True:
            try:
                port = randrange(10240, 65535)
                server = DelayingHTTPServer('127.0.0.1', port, ttfb, response)
                break
            except OSError:
                # port is in use, try another
                continue
        server_thread= Thread(target=server.serve_forever)
        server_thread.start()

        yield port

        server.shutdown()
        # server_thread will finish now

    return server


@pytest_asyncio.fixture(scope='module')
async def test_database():
    config = load_config()['db']
    config['database'] = 'testdb'

    await initialize_pool(**config)

    script = (Path(__file__).parent.parent / 'db/structure.sql').read_text()
    async with get_pool().acquire() as conn:
        await conn.execute(script)
        await conn.executemany(
            'INSERT INTO watchlist (url, interval) VALUES ($1, $2)',
            [
                ('https://httpbin.org/status/200', 1),
                ('https://httpbin.org/status/201', 2),
                ('https://httpbin.org/status/202', 3)
            ],
        )

        yield

        await conn.execute('DROP TABLE IF EXISTS check_log')
        await conn.execute('DROP TABLE IF EXISTS watchlist')
