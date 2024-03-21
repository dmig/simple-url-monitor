# pylint:disable=C0114,C0115,C0116
import asyncio
from unittest.mock import patch
import pytest

from lib.checker import CheckResult
from lib.db import get_pool
from lib.scheduler import main_loop


pytestmark = pytest.mark.asyncio(scope="module")


async def test_clean_db(test_database):
    async with get_pool().acquire() as conn:
        data = await conn.fetch('select * from watchlist')

        assert len(data) == 3

        data = await conn.fetch('select * from check_log')

        assert len(data) == 0


async def test_scheduler(test_database):
    with patch('lib.checker.check_url', return_value=CheckResult(status_code=200)) as p:
        scheduler = asyncio.create_task(main_loop({'interval': 1, 'max_concurrency': 3}))

        with pytest.raises(TimeoutError):
            await asyncio.wait_for(scheduler, 5)

    async with get_pool().acquire() as conn:
        data = await conn.fetch('select url, last_start, "interval", count(cl.wl_id) cnt '
                                 'from watchlist wl '
                                 'left join check_log cl on cl.wl_id = wl.id '
                                 'group by 1,2,3'
                                 )
        for item in data:
            assert item['last_start'] is not None, item['url'] + ' never ran'
            expect = 5 // item['interval']
            assert item['cnt'] >= expect, \
                f"{item['url']} executed only {item['cnt']}/{expect} times"
