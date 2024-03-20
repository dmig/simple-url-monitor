'''
Database routines
'''
import ssl
from typing import Optional
import asyncpg

_pool: asyncpg.Pool = None # type:ignore

async def initialize_pool(cafile: Optional[str] = None, **connect_kwargs):
    '''
    Initialize asyncpg connection pool
    '''
    global _pool  # pylint:disable=W0603

    if _pool:
        return

    if cafile:
        sslctx = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile=cafile)
        sslctx.check_hostname = True
    else:
        sslctx = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        sslctx.check_hostname = False
        sslctx.verify_mode = ssl.CERT_NONE

    connect_kwargs['ssl'] = sslctx

    _pool = await asyncpg.create_pool(**connect_kwargs)  # type: ignore


def get_pool():
    '''
    DB Pool instance wrapper
    '''
    return _pool
