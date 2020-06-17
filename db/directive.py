# SPDX-License-Identifier: GPL-3.0-only
#
# This file is part of the Waymarked Trails Map Project
# Copyright (C) 2020 Sarah Hoffmann

import hug

from .context import DbContext

@hug.directive()
def connection(default=False, context : DbContext=None, **kwargs):
    return context.connection

@hug.directive()
def status_table(default=False, context : DbContext=None, **kwargs):
    return context.tables.status
