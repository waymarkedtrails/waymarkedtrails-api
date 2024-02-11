# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of the Waymarked Trails Map Project
# Copyright (C) 2024 Sarah Hoffmann
import falcon

import sqlalchemy as sa

from ...common.router import Router, needs_db
from ...common.types import Bbox
from ...output.geojson import to_geojson_response

# constants for bbox computation for level 12
MAPWIDTH = 20037508.34
TILEWIDTH = MAPWIDTH/(2**11)

class APITiles(Router):

    def add_routes(self, app, base):
        app.add_route(base + '/12/{x:int(min=0, max=2**12)}/{y:int(min=0, max=2**12)}.json', self)

    @needs_db
    async def on_get(self, conn, req, resp, x, y):
        b = Bbox(x * TILEWIDTH - MAPWIDTH, MAPWIDTH - (y + 1) * TILEWIDTH,
                 (x + 1) * TILEWIDTH - MAPWIDTH, MAPWIDTH - y * TILEWIDTH)

        # Route ways
        d = self.context.db.tables.style.data
        q = sa.select(sa.literal('way').label('type'),
                      d.c.sources.label('top_relations'),
                      d.c.symbol.label('shields'),
                      d.c.novice, d.c.easy, d.c.intermediate, d.c.advanced,
                      d.c.expert, d.c.extreme, d.c.freeride, d.c.downhill,
                      d.c.nordic, d.c.skitour, d.c.sled, d.c.hike, d.c.sleigh,
                      d.c.geom.ST_Intersection(b.as_sql()).ST_AsGeoJSON().label('geometry'))\
              .where(d.c.geom.intersects(b.as_sql()))\
              .order_by(d.c.id)


        elements = list(await conn.execute(q))

        # Joined ways
        d = self.context.db.tables.ways.data
        ws = self.context.db.tables.joined_ways.data

        wayset_id = sa.select(sa.func.array_agg(ws.c.id).label('ids')).where(ws.c.child == d.c.id).scalar_subquery()

        q = sa.select(sa.literal('wayset').label('type'),
                      d.c.id.label('way_id'),
                      wayset_id.label('wayset_ids'),
                      d.c.symbol.label('shield'),
                      d.c.difficulty, d.c.piste, # TODO: take apart
                      d.c.geom.ST_Intersection(b.as_sql()).ST_AsGeoJSON().label('geometry'))\
              .where(d.c.geom.intersects(b.as_sql()))\
              .order_by(d.c.id)

        elements.extend(await conn.execute(q))

        to_geojson_response(elements, resp)
