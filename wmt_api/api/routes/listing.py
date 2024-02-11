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
                    .where(s.c.geom.ST_Intersects(bbox.as_sql()))

        sql = sa.select(*RouteItem.make_selectables(r))\
                   .where(r.c.top)\
                   .where(sa.or_(r.c.id.in_(sa.select(h.c.parent).distinct()
                                       .where(h.c.child == rels.subquery().c.rel)),
                                 r.c.id.in_(rels)
                         ))\
                   .limit(limit)\
                   .order_by(sa.desc(r.c.level), r.c.name)

        res = RouteList(bbox=bbox)
        res.add_items(await conn.execute(sql), locale)
        res.to_response(resp)


    @needs_db
    async def on_get_by_ids(self, conn, req, resp):
        relations = params.as_int_list(req, 'relations')
        locale = params.get_locale(req)

        r = self.context.db.tables.routes.data

        sql = sa.select(*RouteItem.make_selectables(r))\
                .where(r.c.id.in_(relations))\
                .order_by(sa.desc(r.c.level), r.c.name)

        res = RouteList(relations=relations)
        res.add_items(await conn.execute(sql), locale)
        res.to_response(resp)


    @needs_db
    async def on_get_search(self, conn, req, resp):
        query = params.as_str(req, 'query')
        limit = params.as_int(req, 'limit', default=20, vmin=1, vmax=100)
        page = params.as_int(req, 'page', default=1, vmin=1, vmax=10)
        locale = params.get_locale(req)

        maxresults = page * limit

        res = RouteList(query=query, page=page)

        r = self.context.db.tables.routes.data
        base = sa.select(*RouteItem.make_selectables(r))

        # First try: exact match of ref
        sql = base.where(sa.func.lower(r.c.ref) == query.lower()).limit(maxresults+1)
        res.add_items(await conn.execute(sql), locale)

        # If that did not work and the search term is a number, maybe a relation
        # number?
        if page > 1:
            res.ignore_next_items((page - 1) * limit)

        if len(res) == 0 and len(query) > 3 and query.isdigit():
            sql = base.where(r.c.id == int(query))
            res.add_items(await conn.execute(sql), locale)
            if len(res) > 0:
                return res.to_response(resp)

        # Second try: fuzzy matching of text
        if len(res) <= maxresults:
            remain = maxresults - len(res)
            # Preselect matches by doing a word match on name and intnames.
            primary_sim = r.c.name + sa.func.jsonb_path_query_array(r.c.intnames,
                                                                    sa.text("'$.*'"),
                                                                    type_=sa.Text)
            primary_sim = primary_sim.op('<->>>', return_type=sa.Float)(query)
            primary_sim = primary_sim.label('sim')

            # Rerank by full match against main name
            second_sim = r.c.name.op('<->', return_type=sa.Float)(query)
            second_sim = second_sim.label('secsim')

            inner = base.add_columns(primary_sim, second_sim)\
                        .order_by(primary_sim)\
                        .limit(min(1100, remain * 10))\
                        .alias('inner')

            # Rerank by full match against main name
            rematch_sim = (inner.c.sim + inner.c.secsim).label('finsim')

            sql = sa.select(inner.c)\
                    .add_columns(rematch_sim)\
                    .order_by(rematch_sim)\
                    .limit(remain)

            minsim = None
            for o in await conn.execute(sql):
                if minsim is None:
                    minsim = o.finsim
                elif o.finsim - 0.3 > minsim:
                    break
                res.add_item(o, locale)

        res.to_response(resp)


    @needs_db
    async def on_get_segments(self, conn, req, resp):
        bbox = params.as_bbox(req, 'bbox')
        relations = params.as_int_list(req, 'relations')

        r = self.context.db.tables.routes.data

        sql = sa.select(r.c.id, r.c.geom.ST_Intersection(bbox.as_sql()).label('geometry'))\
                  .where(r.c.id.in_(relations)).alias()

        sql = sa.select(sa.literal("relation").label('type'),
                        sql.c.id, sql.c.geometry.ST_AsGeoJSON().label('geometry'))\
                .where(sa.not_(sa.func.ST_IsEmpty(sql.c.geometry)))

        to_geojson_response(await conn.execute(sql), resp)


