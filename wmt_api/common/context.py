# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of the Waymarked Trails Map Project
# Copyright (C) 2023 Sarah Hoffmann
import importlib
import logging
from pathlib import Path

import sqlalchemy.ext.asyncio as sa_asyncio
from sqlalchemy.engine.url import URL

from wmt_shields import ShieldFactory

log = logging.getLogger(__name__)

class Context:
    """ Provide global settings and the DB engine for the
        Waymarkedtrails API.
    """

    def __init__(self, mapname, url=None):
        self.mapname = mapname

        try:
            self.config = importlib.import_module(f'wmt_db.config.{mapname}')
        except ModuleNotFoundError:
            log.error("Cannot find DB config for route map named '%s'.", mapname)
            raise

        try:
            api_config = importlib.import_module('wmt_local_config.api')
            self.dem = Path(api_config.DEM_FILE)
        except ModuleNotFoundError:
            log.warning("Cannot find API config. Elevation profiles not available.")
            self.dem = None

        self.shield_factory = ShieldFactory(self.config.ROUTES.symbols, self.config.SYMBOLS)

        try:
            mapdb_pkg = importlib.import_module(
                          f'wmt_db.maptype.{self.config.MAPTYPE}')
        except ModuleNotFoundError:
            log.error("Unknown map type '%s'.", self.config.MAPTYPE)
            raise

        class Options:
            no_engine = True

        self.db = mapdb_pkg.create_mapdb(self.config, Options())

        if url is None:
            url = URL.create('postgresql+psycopg',
                                 database=self.config.DB_NAME,
                                 username=self.config.DB_USER,
                                 password=self.config.DB_PASSWORD)
        self.engine = sa_asyncio.create_async_engine(url, echo=False)
