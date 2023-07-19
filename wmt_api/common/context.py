# SPDX-License-Identifier: GPL-3.0-only
#
# This file is part of the Waymarked Trails Map Project
# Copyright (C) 2020 Sarah Hoffmann

import threading
import importlib
import logging
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine.url import URL

from wmt_shields import ShieldFactory

log = logging.getLogger(__name__)

class ApiContext(object):
    """ Provide global settings and call local context for the
        Waymarkedtrails API.
    """

    @classmethod
    def init_globals(cls, mapname):
        """ Initialise the global context available for all calls.
            The context is saved in the form of class variables.
            `mapname` describes the name of the map to initialise. The wmt_db
            and wmt_api configurations  with the corresponding name are
            loaded and used.
        """
        cls.mapname = mapname

        try:
            cls.db_config = importlib.import_module(f'wmt_db.config.{mapname}')
        except ModuleNotFoundError:
            log.error("Cannot find DB config for route map named '%s'.", mapname)
            raise

        try:
            api_config = importlib.import_module('wmt_local_config.api')
            cls.dem = Path(api_config.DEM_FILE)
        except ModuleNotFoundError:
            log.warning("Cannot find API config. Elevation profiles not available.")
            cls.dem = None

        cls.shield_factory = ShieldFactory(cls.db_config.ROUTES.symbols,
                                           cls.db_config.SYMBOLS)

        cls.thread_data = threading.local()

        try:
            mapdb_pkg = importlib.import_module(
                          f'wmt_db.maptype.{cls.db_config.MAPTYPE}')
        except ModuleNotFoundError:
            log.error("Unknown map type '%s'.", cls.db_config.MAPTYPE)
            raise

        class Options:
            no_engine = True

        cls.tables = mapdb_pkg.create_mapdb(cls.db_config, Options())
        cls.create_engine()

    @classmethod
    def create_engine(cls):
        cls.engine = create_engine(URL('postgresql',
                                       database=cls.db_config.DB_NAME,
                                       username=cls.db_config.DB_USER,
                                       password=cls.db_config.DB_PASSWORD
                                      ), echo=False)

    @property
    def connection(self):
        """ Get the database connection for the current thread. If none
            exists, one will be implicitly created.
        """
        if not hasattr(self.thread_data, 'conn'):
            self.thread_data.conn = \
                self.engine.connect().execution_options(isolation_level="AUTOCOMMIT")
        return self.thread_data.conn
