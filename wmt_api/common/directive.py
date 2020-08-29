# SPDX-License-Identifier: GPL-3.0-only
#
# This file is part of the Waymarked Trails Map Project
# Copyright (C) 2020 Sarah Hoffmann

import hug

from .context import ApiContext

@hug.directive()
def connection(default=False, context : ApiContext=None, **kwargs):
    return context.connection

@hug.directive()
def status_table(default=False, context : ApiContext=None, **kwargs):
    return context.tables.status

@hug.directive()
def tables(default=False, context : ApiContext=None, **kwargs):
    return context.tables

@hug.directive()
def shield_factory(default=False, context : ApiContext=None, **kwargs):
    return context.shield_config

@hug.directive()
def db_config(default=False, context : ApiContext=None, **kwargs):
    return context.db_config
