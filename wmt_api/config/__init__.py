# SPDX-License-Identifier: GPL-3.0-only
#
# This file is part of the Waymarked Trails Map Project
# Copyright (C) 2020 Sarah Hoffmann

import importlib
import os

class ApiConfig(object):

    def __init__(self):
        self.mapname = os.environ['WMT_CONFIG']

        try:
            self.db = importlib.import_module('wmt_db.config.' + self.mapname)
        except ModuleNotFoundError:
            print("Cannot find DB config for route map named '{}'.".format(self.mapname))
            raise

        try:
            self.api = importlib.import_module('wmt_api.config.' + self.mapname)
        except ModuleNotFoundError:
            print("Cannot find DB config for route map named '{}'.".format(self.mapname))
            raise

        self.shield_factory = ShieldFactory(self.db.ROUTES.symbols,
                                            self.db.SYMBOLS)
