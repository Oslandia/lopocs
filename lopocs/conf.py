# -*- coding: utf-8 -*-

import os


class Config(object):

    BB = None
    DEPTH = 6
    CACHE_DIR = os.path.join(os.path.expanduser("~"), ".cache/lopocs")
    MAX_PATCHS_PER_QUERY = None
    MAX_POINTS_PER_PATCH = None
    POTREE_SCH_PCID_SCALE_01 = 2  # scale 0.1
    POTREE_SCH_PCID_SCALE_001 = 2  # scale 0.01
    USE_MORTON = True
    DEBUG = False
    STATS = True
    STATS_SERVER_PORT = 6379

    CESIUM_COLOR = "colors"

    @classmethod
    def init(cls, config):

        if 'BB' in config:
            l = config['BB']
            cls.BB = {}
            cls.BB['xmin'] = l[0]
            cls.BB['ymin'] = l[1]
            cls.BB['zmin'] = l[2]
            cls.BB['xmax'] = l[3]
            cls.BB['ymax'] = l[4]
            cls.BB['zmax'] = l[5]

        if 'DEPTH' in config:
            cls.DEPTH = config['DEPTH']

        if 'CACHE_DIR' in config:
            cls.CACHE_DIR = config['CACHE_DIR']
            if not os.path.isdir(cls.CACHE_DIR):
                os.makedirs(cls.CACHE_DIR)

        if 'MAX_PATCHS_PER_QUERY' in config:
            cls.MAX_PATCHS_PER_QUERY = config['MAX_PATCHS_PER_QUERY']

        if 'MAX_POINTS_PER_PATCH' in config:
            cls.MAX_POINTS_PER_PATCH = config['MAX_POINTS_PER_PATCH']

        if 'POTREE_SCH_PCID_SCALE_01' in config:
            cls.POTREE_SCH_PCID_SCALE_01 = config['POTREE_SCH_PCID_SCALE_01']

        if 'POTREE_SCH_PCID_SCALE_001' in config:
            cls.POTREE_SCH_PCID_SCALE_001 = config['POTREE_SCH_PCID_SCALE_001']

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
