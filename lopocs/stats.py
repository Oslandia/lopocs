# -*- coding: utf-8 -*-

import redis
from .conf import Config


class Stats():

    r = None

    @classmethod
    def set(cls, n, t):
        cls.r.set('npoints', str(n).encode('utf-8'))
        cls.r.set('time_msec', str(t).encode('utf-8'))

    @classmethod
    def get(cls):
        stats = {}

        t = int(cls.r.get('time_msec').decode('utf-8'))
        stats['time_msec'] = t

        n = int(cls.r.get('npoints').decode('utf-8'))
        stats['npoints'] = n

        if t > 0:
            stats['rate_msec'] = n/t
            stats['rate_sec'] = (n/t)*1000
        else:
            stats['rate_msec'] = 0.0
            stats['rate_sec'] = 0.0

        return stats

    @classmethod
    def init(cls):
        cls.r = redis.StrictRedis(host='127.0.0.1',
                                  port=Config.STATS_SERVER_PORT, db=0)
        cls.r.set('rate', str(0.0).encode('utf-8'))
        cls.r.set('npoints', str(0).encode('utf-8'))
        cls.r.set('time_msec', str(0).encode('utf-8'))
