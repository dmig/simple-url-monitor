'''
Testing fixtures
'''

from contextlib import contextmanager
from random import randrange
from threading import Thread

import pytest
from tests.lib.http_server import DelayingHTTPServer

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
