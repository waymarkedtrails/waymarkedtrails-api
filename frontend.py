# SPDX-License-Identifier: GPL-3.0-only
#
# This file is part of the Waymarked Trails Map Project
# Copyright (C) 2020 Sarah Hoffmann

from wmt_api import api
from wmt_api.db.context import DbContext
import hug

@hug.context_factory()
def create_context(*args, **kwargs):
    return DbContext('hiking', database='planet')

hug.API(__name__).extend(api, '/api')

application = __hug_wsgi__
