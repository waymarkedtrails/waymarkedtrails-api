# SPDX-License-Identifier: GPL-3.0-only
#
# This file is part of the Waymarked Trails Map Project
# Copyright (C) 2022-2023 Sarah Hoffmann
import hug
import sqlalchemy as sa
from io import StringIO

from ...common import directive
from ...common.types import Bbox
from ...common.formatter import format_as_geojson

# constants for bbox computation for level 12
MAPWIDTH = 20037508.34
TILEWIDTH = MAPWIDTH/(2**11)

@hug.get('/{zoom}/{x}/{y}.json', output=format_as_geojson)
def vector_tile(conn: directive.connection, tables: directive.tables,
                zoom: hug.types.in_range(12, 13),
                x: hug.types.in_range(0, 2**12),
                y: hug.types.in_range(0, 2**12)):
    "Return a vector tile with the route data."

    b = Bbox((x * TILEWIDTH - MAPWIDTH, MAPWIDTH - (y + 1) * TILEWIDTH,
             (x + 1) * TILEWIDTH - MAPWIDTH, MAPWIDTH - y * TILEWIDTH))

    # Route ways
    d = tables.style.data
    q = sa.select(sa.literal('way').label('type'),
                  d.c.sources.label('top_relations'),
                  d.c.symbol.label('shields'),
                  d.c.novice, d.c.easy, d.c.intermediate, d.c.advanced,
                  d.c.expert, d.c.extreme, d.c.freeride, d.c.downhill,
                  d.c.nordic, d.c.skitour, d.c.sled, d.c.hike, d.c.sleigh,
                  d.c.geom.ST_Intersection(b.as_sql()).ST_AsGeoJSON().label('geometry'))\
          .where(d.c.geom.intersects(b.as_sql()))\
          .order_by(d.c.id)


    elements = list(conn.execute(q))

    # Joined ways
    d = tables.ways.data
    ws = tables.joined_ways.data

    wayset_id = sa.select(sa.func.array_agg(ws.c.id).label('ids')).where(ws.c.child == d.c.id).scalar_subquery()

    q = sa.select(sa.literal('wayset').label('type'),
                  d.c.id.label('way_id'),
                  wayset_id.label('wayset_ids'),
                  d.c.symbol.label('shield'),
                  d.c.difficulty, d.c.piste, # TODO: take apart
                  d.c.geom.ST_Intersection(b.as_sql()).ST_AsGeoJSON().label('geometry'))\
          .where(d.c.geom.intersects(b.as_sql()))\
          .order_by(d.c.id)

    elements.extend(list(conn.execute(q)))

    return elements
