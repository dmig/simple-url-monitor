#!/usr/bin/env python3
# pylint:disable=C0114

import asyncio
import logging
from typing import Any

from lib.config import load_config
from lib.db import initialize_pool
from lib.scheduler import main_loop


def _task_exception_handler(_, context: dict[str, Any]):
    if 'exception' in context:
        e = context.pop("exception")
        logging.exception('Background task exception: %s, %r',
                           context.pop('message'), context,
                           exc_info=e)
    else:
        logging.error('Background task exception: %s, %r',
                       context.pop('message'), context)


if __name__ == '__main__':
    config = load_config()
    logging.basicConfig()

    loop = asyncio.get_event_loop()
    loop.set_exception_handler(_task_exception_handler)
    loop.run_until_complete(initialize_pool(config['db']))
    loop.run_until_complete(main_loop(config))
