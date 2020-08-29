# SPDX-License-Identifier: GPL-3.0-only
#
# This file is part of the Waymarked Trails Map Project
# Copyright (C) 2020 Sarah Hoffmann

import hug
from os import path as osp

from ..common.directive import shield_factory, db_config

@hug.format.content_type('image/svg+xml')
def format_as_shield(data, request=None, response=None):
    return data.create_image('svg')

@hug.get('/from_tags/{style}', output=format_as_shield)
def from_tags(style: str, factory: shield_factory, **kwargs) -> 'SVG image of a shield':
    """ Create a route shield from a set of OSM tags. The tag list must be
        given as keyword parameters."""
    sym = factory.create(kwargs, '', style=style)
    if sym is None:
        raise hug.HTTPNotFound()

    return sym

@hug.get('/id/{symbol}', output=hug.output_format.file)
def uuid(symbol: str, cfg: db_config):
    """ Retrive a symbol SVG by its ID. These are the IDs returned by the API
        for the routes."""
    if not '.' in symbol:
        symbol += '.svg'
    filename = osp.join(cfg.ROUTES.symbol_datadir, symbol)

    if not osp.exists(filename):
        raise hug.HTTPNotFound()

    return filename
