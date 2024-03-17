'''
Configuration loader module
'''
import os
import tomllib


def load_config(filename = 'settings.toml'):
    '''
    Try to load TOML configuration file
    '''
    if not os.path.exists(filename):
        raise FileNotFoundError(f'{filename} not found')

    with open(filename, 'rb') as fp:
        return tomllib.load(fp)
