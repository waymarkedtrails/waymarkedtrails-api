# SPDX-License-Identifier: GPL-3.0-only
#
# This file is part of the Waymarked Trails Map Project
# Copyright (C) 2020 Sarah Hoffmann

import hug
from typing import NamedTuple

from . import symbols
from ..common.directive import connection, status_table

class StatusOutput(NamedTuple):
    server_status: str
    last_update: str

@hug.get(versions=1)
@hug.cli(output=hug.output_format.json)
def status(conn: connection, status: status_table) :
    """ Return the current status of the API in JSON format.
    """
    res = status.get_date(conn, part='base')

    if not res:
        return StatusOutput('DOWN', '')

    return StatusOutput('OK', res.isoformat())


@hug.extend_api('/symbols')
def symbols_api():
    "The symbols API returns shields for routes."
    return [symbols]
