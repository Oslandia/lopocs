# -*- coding: utf-8 -*-
import io
import os
import sys
import logging
from pathlib import Path

from flask import Flask
from yaml import load as yload

from lopocs.app import api
from lopocs.database import Session
from lopocs.conf import Config

# lopocs version
__version__ = '0.1.dev0'

logger = logging.getLogger(__name__)

# constants for logger
BLACK, RED, GREEN, YELLOW, BLUE, CYAN, WHITE = list(range(7))

COLORS = {
    'CRITICAL': RED,
    'ERROR': RED,
    'WARNING': YELLOW,
    'INFO': GREEN,
    'DEBUG': CYAN,
}

LOG_LEVELS = {
    'debug': logging.DEBUG,
    'info': logging.INFO,
    'warning': logging.WARNING,
    'error': logging.ERROR,
    'critical': logging.CRITICAL
}

COLOR_SEQ = "\033[1;%dm"
RESET_SEQ = "\033[0m"
BOLD_SEQ = "\033[1m"


def formatter_message(message, use_color=True):
    if use_color:
        message = message.replace("$RESET", RESET_SEQ)
        message = message.replace("$BOLD", BOLD_SEQ)
    else:
        message = message.replace("$RESET", "").replace("$BOLD", "")
    return message


class ColoredFormatter(logging.Formatter):

    def __init__(self, msg, use_color=True):
        logging.Formatter.__init__(self, msg)
        self.use_color = use_color

    def format(self, record):
        try:
            msg = record.msg.split(':', 1)
            if len(msg) == 2:
                record.msg = '[%-12s]%s' % (msg[0], msg[1])
        except:
            pass
        levelname = record.levelname
        if self.use_color and levelname in COLORS:
            levelname_color = (
                COLOR_SEQ % (30 + COLORS[levelname]) + levelname + RESET_SEQ)
            record.levelname = levelname_color
        return logging.Formatter.format(self, record)


console = logging.StreamHandler()
color_fmt = formatter_message('[%(asctime)s][%(levelname)-18s][%(module)s] %(message)s')
formatter = ColoredFormatter(color_fmt, use_color=True)
console.setFormatter(formatter)
logger.addHandler(console)


def set_level(level='info'):
    """
    Set log level
    """
    logger.setLevel(LOG_LEVELS.get(level))


def load_yaml_config(filename):
    """
    Open Yaml file, load content for flask config and returns it as a python dict
    """
    content = io.open(filename, 'r').read()
    return yload(content).get('flask', {})


def create_app(env='Defaults'):
    """
    Creates application.
    :returns: flask application instance
    """
    app = Flask(__name__)
    cfgfile = os.environ.get('LOPOCS_SETTINGS')
    if cfgfile:
        app.config.update(load_yaml_config(cfgfile))
    else:
        try:
            cfgfile = (Path(__file__).parent / '..' / 'conf' / 'lopocs.yml').resolve()
        except FileNotFoundError:
            logger.warning('no config file found !!')
            sys.exit(1)
    app.config.update(load_yaml_config(str(cfgfile)))
    print(str(cfgfile))
    set_level(app.config['LOG_LEVEL'])
    logger.debug('loading config from {}'.format(cfgfile))

    # load extensions
    api.init_app(app)
    Session.init_app(app)
    Config.init(app.config)

    return app
