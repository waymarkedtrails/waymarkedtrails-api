# SPDX-License-Identifier: GPL-3.0-only
#
# This file is part of the Waymarked Trails Map Project
# Copyright (C) 2020 Sarah Hoffmann

import hug
from typing import NamedTuple
from datetime import datetime as dt

import sqlalchemy as sa

from wmt_shields import ShieldFactory
from wmt_shields.wmt_config import WmtConfig

from api import listings, tiles
from api.details import base as details
import db.directive

# XXX configure
shield_factory = ShieldFactory(
                ('.slope_symbol',
                 '.nordic_symbol',
                 '.image_symbol',
                 '.cai_hiking_symbol',
                 '.swiss_mobile',
                 '.jel_symbol',
                 '.kct_symbol',
                 '.osmc_symbol',
                 '.ref_color_symbol',
                 '.ref_symbol',
                 '.color_box'
                ), WmtConfig())

class StatusOutput(NamedTuple):
    server_status: str
    last_update: str

@hug.get(versions=1)
def status(conn: db.directive.connection,
           status: db.directive.status_table) -> StatusOutput:
    """ Return the current status of the API in JSON format.
    """
    res = conn.scalar(sa.select([status.c.date]).where(status.c.part == 'base'))

    if not res:
        return StatusOutput('DOWN', '')

    return StatusOutput('OK', res)

@hug.format.content_type('image/svg+xml')
def format_as_shield(data, request=None, response=None):
    return data.create_image('svg')

@hug.get(output=format_as_shield)
def symbols(**kwargs) -> 'SVG image of a shield':
    """ Create a route shield from a set of OSM tags. The tag list must be
        given as keyword parameters."""
    sym = shield_factory.create(kwargs, '', style='NAT')
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
