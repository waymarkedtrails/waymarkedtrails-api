# SPDX-License-Identifier: GPL-3.0-only
#
# This file is part of the Waymarked Trails Map Project
# Copyright (C) 2020 Sarah Hoffmann

import hug
import threading

from sqlalchemy import create_engine
from sqlalchemy.engine.url import URL

from .tables import RouteTables

class DbContext(object):

    def __init__(self, schema, **kwargs):
        self.engine = create_engine(URL('postgresql', **kwargs), echo=False)
        self.thread_data = threading.local()
        self.tables = RouteTables(schema)

    @property
    def connection(self):
        if not hasattr(self.thread_data, 'conn'):
            self.thread_data.conn = \
                self.engine.connect().execution_options(autocommit=True)
        return self.thread_data.conn
