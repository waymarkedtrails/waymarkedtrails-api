# SPDX-License-Identifier: GPL-3.0-only
#
# This file is part of the Waymarked Trails Map Project
# Copyright (C) 2020 Sarah Hoffmann

import hug

from . import relation
from . import guidepost

@hug.extend_api('/relation/{oid}')
def relation_details():
    return [relation]

@hug.extend_api('/guidepost/{oid}')
def guidepost_details():
    return [guidepost]
