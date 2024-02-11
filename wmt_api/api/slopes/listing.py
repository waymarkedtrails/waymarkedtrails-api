# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of the Waymarked Trails Map Project
# Copyright (C) 2024 Sarah Hoffmann
import falcon

import sqlalchemy as sa

from ...common.router import Router, needs_db
from ...common import params
from ...output.route_list import RouteList
from ...output.route_item import RouteItem
from ...output.geojson import to_geojson_response

class APIListing(Router):

    def add_routes(self, app, base):
        app.add_route(base + '/by_area', self, suffix='by_area')
        app.add_route(base + '/by_ids', self, suffix='by_ids')
        app.add_route(base + '/search', self, suffix='search')
        app.add_route(base + '/segments', self, suffix='segments')


    @needs_db
    async def on_get_by_area(self, conn, req, resp):
        bbox = params.as_bbox(req, 'bbox')
        limit = params.as_int(req, 'limit', default=20, vmin=1, vmax=100)
        locale = params.get_locale(req)

        r = self.context.db.tables.routes.data
        s = self.context.db.tables.segments.data
        h = self.context.db.tables.hierarchy.data

        rels = sa.select(sa.func.unnest(s.c.rels).label('rel')).distinct()\
                    .where(s.c.geom.ST_Intersects(bbox.as_sql())).alias()

        sels = RouteItem.make_selectables(r)
        sels.append(sa.literal('relation').label('type'))
        sql = sa.select(*sels)\
                   .where(r.c.top)\
                   .where(sa.or_(r.c.id.in_(sa.select(h.c.parent).distinct()
                                       .where(h.c.child == rels.c.rel)),
                                 r.c.id.in_(rels)
                         ))\
                   .limit(limit)\
                   .order_by(sa.desc(r.c.piste), r.c.name)

        res = RouteList(bbox=bbox)
        res.add_items(await conn.execute(sql), locale)

        if len(res) < limit:
            w = self.context.db.tables.ways.data
            ws = self.context.db.tables.joined_ways.data
            sql = sa.select(sa.func.coalesce(ws.c.id, w.c.id).label('id'),
                            sa.case((ws.c.id == None, 'way'), else_='wayset').label('type'),
                            w.c.name, w.c.intnames, w.c.symbol,
                            w.c.piste).distinct()\
                    .select_from(w.outerjoin(ws, w.c.id == ws.c.child))\
                    .where(w.c.geom.ST_Intersects(bbox.as_sql()))\
                    .order_by(w.c.name)\
                    .limit(limit - len(res))

            res.add_items(await conn.execute(sql), locale)

        res.to_response(resp)


    @needs_db
    async def on_get_by_ids(self, conn, req, resp):
        relations = params.as_int_list(req, 'relations', default='')
        ways = params.as_int_list(req, 'ways', default='')
        waysets = params.as_int_list(req, 'waysets', default='')
        locale = params.get_locale(req)

        res = RouteList(relations=relations, ways=ways, waysets=waysets)

        if relations:
            r = self.context.db.tables.routes.data

            sels = RouteItem.make_selectables(r)
            sels.append(sa.literal('relation').label('type'))

            sql = sa.select(*sels).where(r.c.id.in_(relations))

            res.add_items(await conn.execute(sql), locale)

        if ways:
            w = self.context.db.tables.ways.data

            sels = RouteItem.make_selectables(w)
            sels.append(sa.literal('way').label('type'))

            sql = sa.select(*sels).where(w.c.id.in_(ways))

            res.add_items(await conn.execute(sql), locale)

        if waysets:
            w = self.context.db.tables.ways.data

            sels = RouteItem.make_selectables(w)
            sels.append(sa.literal('wayset').label('type'))

            sql = sa.select(*sels).where(w.c.id.in_(waysets))

            res.add_items(await conn.execute(sql), locale)

        res.to_response(resp)


    @needs_db
    async def on_get_search(self, conn, req, resp):
        query = params.as_str(req, 'query')
        limit = params.as_int(req, 'limit', default=20, vmin=1, vmax=100)
        page = params.as_int(req, 'page', default=1, vmin=1, vmax=10)
        locale = params.get_locale(req)

        maxresults = page * limit

        r = self.context.db.tables.routes.data
        sels = RouteItem.make_selectables(r)
        sels.append(sa.literal('relation').label('type'))
        rbase = sa.select(*sels)

        w = self.context.db.tables.ways.data
        ws = self.context.db.tables.joined_ways.data
        wbase = sa.select(sa.func.coalesce(ws.c.id, w.c.id).label('id'),
                          sa.case((ws.c.id == None, 'way'), else_='wayset').label('type'),
                          w.c.name, w.c.intnames, w.c.symbol,
                          w.c.piste).distinct()\
                  .select_from(w.outerjoin(ws, w.c.id == ws.c.child))

        todos = ((r, rbase), (w, wbase))

        objs = RouteList(query=query, page=page)

        # First try: exact match of ref
        for t, base in todos:
            if len(objs) <= maxresults:
                refmatch = base.where(t.c.name == '[%s]' % query).limit(maxresults - len(objs) + 1)
                objs.add_items(await conn.execute(refmatch), locale)

        # If that did not work and the search term is a number, maybe a relation
        # number?
        if not objs and len(query) > 3 and query.isdigit():
            for t, base in todos:
                idmatch = base.where(t.c.id == int(query))
                objs.add_items(await conn.execute(idmatch), locale)

            if objs:
                return objs.to_response(resp)

        # Second try: fuzzy matching of text
        for t, base in todos:
            if len(objs) <= maxresults:
                sim = sa.func.similarity(t.c.name, query)
                res = base.add_columns(sim.label('sim'))\
                        .where(t.c.name.notlike('(%'))\
                        .order_by(sa.desc(sim))\
                        .limit(maxresults - len(objs) + 1)
                if objs:
                    res = res.where(sim > 0.5)
                else:
                    res = res.where(sim > 0.1)

                maxsim = None
                for r in await conn.execute(res):
                    if maxsim is None:
                        maxsim = r.sim
                    elif maxsim > r.sim * 3:
                        break
                    objs.add_item(r, locale)

        objs.to_response(resp)


    @needs_db
    async def on_get_segments(self, conn, req, resp):
        bbox = params.as_bbox(req, 'bbox')
        relations = params.as_int_list(req, 'relations', default='')
        ways = params.as_int_list(req, 'ways', default='')
        waysets = params.as_int_list(req, 'waysets', default='')

        objs = []

        if relations:
            r = self.context.db.tables.routes.data
            sql = sa.select(sa.literal("relation").label('type'), r.c.id,
                            r.c.geom.ST_Intersection(bbox.as_sql()).label('geometry'))\
                    .where(r.c.id.in_(relations)).alias()

            sql = sa.select(sql.c.type, sql.c.id, sql.c.geometry.ST_AsGeoJSON().label('geometry'))\
                    .where(sa.not_(sa.func.ST_IsEmpty(sql.c.geometry)))

            for x in await conn.execute(sql):
                objs.append(x)

        if ways:
            w = self.context.db.tables.ways.data
            sql = sa.select(sa.literal("way").label('type'), w.c.id,
                            w.c.geom.ST_Intersection(bbox.as_sql()).label('geometry'))\
                    .where(w.c.id.in_(ways)).alias()

            sql = sa.select(sql.c.type, sql.c.id, sql.c.geometry.ST_AsGeoJSON().label('geometry'))\
                    .where(sa.not_(sa.func.ST_IsEmpty(sql.c.geometry)))

            for x in await conn.execute(sql):
                objs.append(x)

        if waysets:
            ws = self.context.db.tables.joined_ways.data
            sql = sa.select(sa.literal("wayset").label('type'),
                            ws.c.id.label('id'),
                            sa.func.ST_CollectionHomogenize(
                                 sa.func.ST_Collect(w.c.geom.ST_Intersection(bbox.as_sql()))).label('geometry')
                           )\
                    .select_from(w.join(ws, w.c.id == ws.c.child))\
                    .where(ws.c.id.in_(waysets)).group_by(ws.c.id).alias()

            sql = sa.select(sql.c.type, sql.c.id, sql.c.geometry.ST_AsGeoJSON().label('geometry'))\
                    .where(sa.not_(sa.func.ST_IsEmpty(sql.c.geometry)))

            for x in await conn.execute(sql):
                objs.append(x)

        to_geojson_response(objs, resp)

