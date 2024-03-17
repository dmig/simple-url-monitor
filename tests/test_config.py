# pylint:disable=C0114,C0115,C0116
from tempfile import NamedTemporaryFile
import tomllib
import pytest
from lib.config import load_config


def test_load_config():
    with NamedTemporaryFile() as fp:
        fp.writelines([
            b'[section]\n',
            b'key="value"\n',
            b'float=1.0\n',
            b'bool=1\n',
        ])
        fp.flush()

        cfg = load_config(fp.name)

    assert cfg == {'section': {'key': 'value', 'float': 1.0, 'bool': True}}


def test_load_config_fail():
    with NamedTemporaryFile() as fp:
        fp.writelines([
            b'key=badvalue\n',
        ])
        fp.flush()

        with pytest.raises(tomllib.TOMLDecodeError):
            load_config(fp.name)
