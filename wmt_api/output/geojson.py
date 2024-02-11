# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of the Waymarked Trails Map Project
# Copyright (C) 2024 Sarah Hoffmann

from ..common.json_writer import JsonWriter

def to_geojson_response(objs, response):
    out = JsonWriter().start_object()\
                      .keyval('type', 'FeatureCollection')

    out.key('crs').raw('{"type": "name", "properties": {"name": "EPSG:3857"}}').next()
    out.key('features').start_array()

    for obj in objs:
        out.start_object()\
           .keyval('type', 'Feature')\
           .key('geometry').raw(obj.geometry).next()

        if 'id' in obj._fields:
            out.keyval('id', obj.id)

        if len(obj._fields) > 2:
            out.key('properties').start_object()
            for k, v in obj._mapping.items():
                if k not in ('id', 'geometry'):
                    out.keyval(k, v)
            out.end_object()

        out.end_object().next()

    out.end_array().end_object()
    out.to_response(response)
