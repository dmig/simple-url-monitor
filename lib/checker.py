'''
Response checking and timing routines
'''
import logging
import re
from time import perf_counter_ns
from dataclasses import dataclass
from typing import Optional
import httpx


@dataclass
class CheckResult:  # pylint:disable=C0115
    connection: int = -1
    ttfb: int = -1
    response: int = -1
    status_code: int = -1
    content_check: Optional[bool] = None
    error_message: Optional[str] = None


_logger = logging.getLogger(__name__)

async def check_url(url: str, content_re: Optional[str] = None) -> CheckResult:
    '''
    Main URL checking worker routine
    '''

    result = CheckResult()
    tm0 = 0

    async def _trace_times(event_name, info):
        nonlocal tm0

        if event_name == 'connection.connect_tcp.started':
            tm0 = perf_counter_ns()
        elif event_name in ('connection.connect_tcp.complete', 'connection.start_tls.complete',
                            'http2.send_connection_init.complete'):
            result.connection = (perf_counter_ns() - tm0) // 1000000  # truncate to milliseconds
        elif event_name in ('http2.receive_response_headers.started',
                            'http11.receive_response_headers.started'):
            # BUG this event doesn't represent data receive event, but begin wait for data
            result.ttfb = (perf_counter_ns() - tm0) // 1000000  # truncate to milliseconds
        elif event_name in ('http2.receive_response_body.complete',
                            'http11.receive_response_body.complete'):
            result.response = (perf_counter_ns() - tm0) // 1000000  # truncate to milliseconds

    async with httpx.AsyncClient(http2=True,
                                 follow_redirects=False,
        try:
            response = await client.get(url, extensions={'trace': _trace_times})
            result.status_code = response.status_code

            if content_re:
                try:
                    result.content_check = bool(re.search(content_re, response.text,
                                                            re.MULTILINE | re.DOTALL))
                except re.error as e:
                    _logger.error('Invalid content_re (%r): %s', content_re, e)
                    result.error_message = str(e)
        except httpx.TransportError as e:
            _logger.error('%r: %r', url, e)
            # exception may have an empty message
            result.error_message = str(e) or e.__class__.__name__

    return result
