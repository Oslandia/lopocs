# -*- coding: utf-8 -*-

class Config(object):

    BB = None
    DEPTH = 6
    METHOD = None # random / midoc
    LIMIT = 10000 # morton

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

        if 'METHOD' in config:
            cls.METHOD = config['METHOD']

        if 'LIMIT' in config:
            cls.LIMIT = config['LIMIT']
