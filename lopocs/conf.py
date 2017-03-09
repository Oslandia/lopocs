# -*- coding: utf-8 -*-

import os


class Config(object):

    DEPTH = 6
    CACHE_DIR = os.path.join(os.path.expanduser("~"), ".cache", "lopocs")
    ROOT_HCY = None
    MAX_PATCHS_PER_QUERY = None
    MAX_POINTS_PER_PATCH = None
    USE_MORTON = True
    DEBUG = False
    STATS = False
    STATS_SERVER_PORT = 6379

    CESIUM_COLOR = "colors"

    @classmethod
    def init(cls, config):

        if 'DEPTH' in config:
            cls.DEPTH = config['DEPTH']

        if 'CACHE_DIR' in config:
            cls.CACHE_DIR = config['CACHE_DIR']
            if not os.path.isdir(cls.CACHE_DIR):
                os.makedirs(cls.CACHE_DIR)

        if 'ROOT_HCY' in config:
            cls.ROOT_HCY = config['ROOT_HCY']

        if 'MAX_POINTS_PER_PATCH' in config:
            cls.MAX_POINTS_PER_PATCH = config['MAX_POINTS_PER_PATCH']

        if 'USE_MORTON' in config:
            cls.USE_MORTON = config['USE_MORTON']

        if 'DEBUG' in config:
            cls.DEBUG = config['DEBUG']

        if 'STATS' in config:
            cls.STATS = config['STATS']

        if 'STATS_SERVER_PORT' in config:
            cls.STATS_SERVER_PORT = config['STATS_SERVER_PORT']

        if 'CESIUM_COLOR' in config:
            cls.CESIUM_COLOR = config['CESIUM_COLOR']
