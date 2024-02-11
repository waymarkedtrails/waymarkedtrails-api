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
        q = sa.select(sa.literal('way').label('type'), d.c.toprels.label('top_relations'),
                      d.c.cldrels.label('child_relations'),
                      d.c.inrshields.concat(d.c.lshields).label('shields'),
                      d.c.style, d.c['class'],
                      d.c.geom.ST_Intersection(b.as_sql()).label('geometry'))\
              .where(d.c.geom.intersects(b.as_sql()))\
              .order_by(d.c.id)\
              .subquery()

        q = sa.select(q.c.type, q.c.top_relations,
                      q.c.child_relations, q.c.shields,
                      q.c.style, q.c['class'],
                      q.c.geometry.ST_AsGeoJSON().label('geometry'))\
              .where(q.c.geometry.ST_GeometryType() == 'ST_LineString')\
              .where(sa.not_(q.c.geometry.ST_IsEmpty()))

        elements = list(await conn.execute(q))

        # Guideposts
        if hasattr(self.context.db.tables, 'guideposts'):
            d = self.context.db.tables.guideposts.data
            q = sa.select(sa.literal('guidepost').label('type'),
                          d.c.id.label('osm_id'), d.c.name, d.c.ele,
                          d.c.geom.ST_AsGeoJSON().label('geometry'))\
                    .where(d.c.geom.intersects(b.as_sql()))\
                    .order_by(d.c.id)

            elements.extend(await conn.execute(q))

        to_geojson_response(elements, resp)
