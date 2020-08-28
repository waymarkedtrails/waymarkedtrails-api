# SPDX-License-Identifier: GPL-3.0-only
#
# This file is part of the Waymarked Trails Map Project
# Copyright (C) 2020 Sarah Hoffmann

import hug
from typing import NamedTuple

from . import listings, tiles
from .details import base as details
from ..db.directive import connection, status_table, shield_factory

hug.defaults.cli_output_format = hug.output_format.json

class StatusOutput(NamedTuple):
    server_status: str
    last_update: str

@hug.get(versions=1)
@hug.cli()
def status(conn: connection, status: status_table) -> StatusOutput:
    """ Return the current status of the API in JSON format.
    """
    res = status.get_date(conn, part='base')

    if not res:
        return StatusOutput('DOWN', '')

    print("AAA", res)
    return StatusOutput('OK', res)

@hug.format.content_type('image/svg+xml')
def format_as_shield(data, request=None, response=None):
    return data.create_image('svg')

@hug.get(output=format_as_shield)
def symbols(factory: shield_factory, **kwargs) -> 'SVG image of a shield':
    """ Create a route shield from a set of OSM tags. The tag list must be
        given as keyword parameters."""
    sym = factory.create(kwargs, '', style='NAT')
    if sym is None:
        raise hug.HTTPNotFound()

    return sym


@hug.extend_api('/list')
def listing_api():
    "The listing API returns route list overviews."
    return [listings]

@hug.extend_api('/details')
def listing_api():
    "The details API returns various detailed information about a single route."
    return [details]

@hug.extend_api('/tiles')
def tiles_api():
    "The tiles API returns vector tiles on level 12."
    return [tiles]
