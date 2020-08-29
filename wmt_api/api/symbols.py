# SPDX-License-Identifier: GPL-3.0-only
#
# This file is part of the Waymarked Trails Map Project
# Copyright (C) 2020 Sarah Hoffmann

import hug

from ..common.directive import shield_factory

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
