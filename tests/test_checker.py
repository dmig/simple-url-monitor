# pylint:disable=C0114,C0115,C0116
import pytest

from lib.checker import check_url


@pytest.mark.asyncio
@pytest.mark.parametrize('ttfb,content,code', [(10,10,200),(100,100,300),(500,500,400),])
async def test_checker_delays(http_server, ttfb, content, code):

    with http_server(ttfb, content) as port:
        res = await check_url(f'http://127.0.0.1:{port}/status/{code}')

    assert res.status_code == code
    assert None not in (res.connection, res.ttfb, res.response) and \
        res.connection <= res.ttfb <= res.response  # type:ignore
    # BUG: due to httpcore limitation, no way to determine actual first byte timestamp
    # assert res.ttfb >= ttfb
    assert res.response >= content + ttfb


@pytest.mark.asyncio
@pytest.mark.parametrize('code,regex,expect', [(200, '[bad regex', None),
                                                  (200, 'Request fulfilled', True),
                                                  (200, '<html.+</html>', True),
                                                  (200, 'no match', False)])
async def test_checker_regex(http_server, code, regex, expect):

    with http_server() as port:
        res = await check_url(f'http://127.0.0.1:{port}/status/{code}', regex)

    assert res.status_code == code
    assert res.content_check == expect
    assert expect is not None or res.error_message


@pytest.mark.asyncio
async def test_checker_unreachable():

    res = await check_url('http://125.125.0.1:1234/status', timeout=1, connect_timeout=1)

    assert res.status_code is None
    assert res.error_message
