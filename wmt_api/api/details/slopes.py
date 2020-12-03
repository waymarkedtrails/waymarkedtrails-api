# SPDX-License-Identifier: GPL-3.0-only
#
# This file is part of the Waymarked Trails Map Project
# Copyright (C) 2020 Sarah Hoffmann
"""
Details API for slope map style.
"""
import hug

from . import relation, way, wayset

@hug.extend_api('/relation/{oid}')
def relation_details():
    return [relation]

@hug.extend_api('/way/{oid}')
def way_details():
    return [way]

@hug.extend_api('/wayset/{oid}')
def wayset_details():
    return [wayset]
