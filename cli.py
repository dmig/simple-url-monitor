#!/usr/bin/env python3
# pylint:disable=C0114,C0116,W0621,W0622

# import asyncio
import argparse
import asyncio
import logging
import re
from typing import Optional
from urllib.parse import urlparse

from lib.config import load_config
from lib.db import initialize_pool, get_pool


def _get_arguments(config):
    def interval(value):
        m = config['scheduler']['interval']
        if not m <= int(value) <= 300:  # not more than 300 sec
            raise ValueError(f'Value must be between {m} and 300')
        return int(value)

    def url(value):
        res = urlparse(value)
        if res.scheme not in ('http', 'https'):
            raise ValueError('Unsupported URL scheme')
        if not res.netloc:
            raise ValueError('Unsupported or invalid URL')
        return value.strip()

    def regex(value):
        try:
            re.compile(value)
        except re.error as e:
            raise ValueError(e.msg) from e
        return value.strip()

    arguments = argparse.ArgumentParser(description='Simple CLI for URL checker service')
    action = arguments.add_subparsers(dest='action', required=True)

    action.add_parser('list', help='list urls')

    act_shw = action.add_parser('show', help='show url details')
    act_shw.add_argument('id', help='Record ID', type=int)

    act_add = action.add_parser('add', help='add url')
    act_add.add_argument('url', help='A valid URL', type=url)
    act_add.add_argument(
        'interval',
        help=f'Check interval (seconds), {config["scheduler"]["interval"]}..300',
        type=interval,
    )
    act_add.add_argument(
        'content_rx', help='Content check regex', nargs='?', type=regex, metavar='regex'
    )

    act_rem = action.add_parser('remove', help='remove url')
    act_rem.add_argument('id', help='Record ID', type=int)

    act_upd = action.add_parser('update', help='update url')
    act_upd.add_argument('id', help='Record ID', type=int)

    act_upd_en = act_upd.add_mutually_exclusive_group()
    act_upd_en.set_defaults(enable=None)
    act_upd_en.add_argument('-e', '--enable', action='store_true', dest='enable')
    act_upd_en.add_argument('-d', '--disable', action='store_false', dest='enable')

    act_upd_re = act_upd.add_mutually_exclusive_group()
    act_upd_re.add_argument(
        '-r', '--regex', help='Update content regex', nargs=1, dest='content_rx', type=regex,
        metavar='REGEX'
    )
    act_upd_re.add_argument(
        '-R',
        '--remove-regex',
        help='Remove content regex',
        action='store_const',
        const=False,
        dest='content_rx',
    )
    act_upd.add_argument(
        '-i',
        '--interval',
        help=f'Set interval (seconds), {config["scheduler"]["interval"]}..300',
        type=interval,
    )

    return arguments.parse_args()


# region Actions
async def action_add(url: str, interval: int, regex: Optional[str]):
    async with get_pool().acquire() as conn:
        new_id = await conn.fetchval(
            'INSERT INTO watchlist (url, "interval", content_rx) '
            'VALUES ($1, $2, $3) RETURNING id',
            url, interval, regex,
        )
        print('Successfully created record with id =', new_id)


async def action_remove(id: int):
    async with get_pool().acquire() as conn:
        ret = await conn.execute('DELETE FROM watchlist WHERE id = $1', id)
        print('Removed ', ret.split(' ')[1], 'records')


async def action_update(id: int, **kwargs):
    updates = []
    values = [id]
    i = 2
    for f, v in kwargs.items():
        if v is not None:
            updates.append(f'{f} = ${i}')
            i += 1
            # for content_rx False means 'set NULL'
            # also, unpack content_rx from list here
            values.append(v if f != 'content_rx' else (v and v[0] or None)) # type:ignore

    # nothing to update
    if not updates:
        print('Nothing to update')
        return

    async with get_pool().acquire() as conn:
        query = 'UPDATE watchlist SET ' + ', '.join(updates) + ' WHERE id = $1'
        ret = await conn.execute(query, *values)
        print('Updated ', ret.split(' ')[1], 'records')


async def action_list():
    list_tpl = '{:>10} {:>1.1} {:>3.3} {:19.19} {:19.19} {:40.40} {:20.20}'
    async with get_pool().acquire() as conn:
        data = await conn.fetch(
            'SELECT id, enable, interval, last_start, url, content_rx '
            'FROM watchlist'
        )
        if not data:
            print('No records')
            return
        print(list_tpl.format(*data[0].keys()))
        print('-' * 100)
        for record in data:
            print(list_tpl.format(*map(str, record.values())))


async def action_show(id: int):
    async with get_pool().acquire() as conn:
        record = await conn.fetchrow(
            'SELECT id, enable, interval, last_start, url, content_rx '
            'FROM watchlist WHERE id = $1', id
        )
        if not record:
            print('Record', id, 'not found')
            return
        for field in record.items():
            print('{:>15}: {}'.format(*field))
# endregion


async def execute(action: str, **kwargs):
    await {
        'add': action_add,
        'remove': action_remove,
        'update': action_update,
        'list': action_list,
        'show': action_show,
    }[action](**kwargs)


if __name__ == '__main__':
    config = load_config()
    logging.basicConfig()

    args = _get_arguments(config)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(initialize_pool(**config['db']))
    loop.run_until_complete(execute(**vars(args)))
