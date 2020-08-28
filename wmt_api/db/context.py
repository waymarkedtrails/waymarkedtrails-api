# SPDX-License-Identifier: GPL-3.0-only
#
# This file is part of the Waymarked Trails Map Project
# Copyright (C) 2020 Sarah Hoffmann

import hug
import threading
import importlib

from sqlalchemy import create_engine
from sqlalchemy.engine.url import URL

from .tables import RouteTables

class DbContext(object):

    @classmethod
    def init_db(cls, config):
        cls.config = config
        cls.engine = create_engine(URL('postgresql',
                                        database=config.db.DB_NAME,
                                        username=config.db.DB_USER,
                                        password=config.db.DB_PASSWORD
                                        ), echo=False)
        cls.thread_data = threading.local()

        try:
            mapdb_pkg = importlib.import_module(
                          'wmt_db.maptype.' + config.db.MAPTYPE)
        except ModuleNotFoundError:
            print("Unknown map type '{}'.".format(config.db.MAPTYPE))
            raise

        class Options:
            no_engine = True

        cls.tables = mapdb_pkg.DB(config.db, Options())

    @property
    def connection(self):
        if not hasattr(self.thread_data, 'conn'):
            self.thread_data.conn = \
                self.engine.connect().execution_options(autocommit=True)
        return self.thread_data.conn
