# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of the Waymarked Trails Map Project
# Copyright (C) 2024 Sarah Hoffmann
import falcon
import sqlalchemy as sa

from ...common import params
from ...common.errors import APIError
from ...common.json_writer import JsonWriter
from ...common.router import Router, needs_db
from ...output.wikilink import get_wikipedia_link
from ...output.route_item import DetailedRouteItem, RouteItem
from ...output.geometry import RouteGeometry
from ...output.elevation import SegmentElevation, get_way_elevation_data

class APIDetailsRelation(Router):

    def add_routes(self, app, base):
        base += '/{oid:int(min=1)}'
        app.add_route(base, self, suffix='info')
        app.add_route(base + '/wikilink', self, suffix='wikilink')
        app.add_route(base + '/geometry/{geomtype}', self, suffix='geometry')
        app.add_route(base + '/way-elevation', self, suffix='way_elevation')


    @needs_db
    async def on_get_info(self, conn, req, resp, oid):
        locale = params.get_locale(req)

        r = self.context.db.tables.routes.data
        h = self.context.db.tables.hierarchy.data

        fields = DetailedRouteItem.make_selectables(r)

        row = (await conn.execute(sa.select(*fields)
                                    .where(r.c.id == oid))).first()

        if row is None:
            raise falcon.HTTPNotFound()

        writer = JsonWriter()
        res = DetailedRouteItem(writer, row, locale, objtype='relation')

        # add subroutes where applicable
        w = sa.select(h.c.child).distinct()\
              .where(h.c.parent == oid)

        sections = await conn.execute(sa.select(*RouteItem.make_selectables(r))\
                                        .where(r.c.id != oid).where(r.c.id.in_(w)))

        if sections.rowcount > 0:
            res.add_extra_route_info('subroutes', sections, locale)

        # add superroutes where applicable
        w = sa.select(h.c.parent).distinct()\
              .where(h.c.child == oid).where(h.c.depth == 2)

        sections = await conn.execute(sa.select(*RouteItem.make_selectables(r))\
                                        .where(r.c.id != oid).where(r.c.id.in_(w)))

        if sections.rowcount > 0:
            res.add_extra_route_info('superroutes', sections, locale)

        res.finish()
        writer.to_response(resp)


    @needs_db
    async def on_get_wikilink(self, conn, req, resp, oid):
        locale = params.get_locale(req)

        r = self.context.db.osmdata.relation.data

        url = get_wikipedia_link(
                 await conn.scalar(sa.select(r.c.tags).where(r.c.id == oid)),
                 locale)

        if url is None:
            raise falcon.HTTPNotFound()

        raise falcon.HTTPSeeOther(url)

    @needs_db
    async def on_get_geometry(self, conn, req, resp, oid, geomtype):
        locale = params.get_locale(req)
        simplify = params.as_int(req, 'simplify',  default=0)
        if geomtype not in ('geojson', 'kml', 'gpx'):
            raise APIError("Supported geometry types are: geojson, kml, gpx")

        r = self.context.db.tables.routes.data

        geom = r.c.geom
        if simplify > 0:
            geom = geom.ST_Simplify(r.c.geom.ST_NPoints()/int(simplify))
        if geomtype == 'geojson' :
            geom = geom.ST_AsGeoJSON()
        else:
            geom = geom.ST_Transform(4326)

        rows = [r.c.name, r.c.intnames, r.c.ref, r.c.id, geom.label('geom')]

        obj = (await conn.execute(sa.select(*rows).where(r.c.id == oid))).first()

        if obj is None:
            raise falcon.HTTPNotFound()

        RouteGeometry(obj, locales=locale, fmt=geomtype).to_response(req, resp)


    @needs_db
    async def on_get_way_elevation(self, conn, req, resp, oid):
        max_segment_len = params.as_int(req, 'simplify',  default=0, vmin=2)
        step = max(max_segment_len/10, min(max_segment_len, 50))

        if self.context.dem is None:
            raise falcon.HTTPRouteNotFound()

        h = self.context.db.tables.hierarchy.data
        s = self.context.db.tables.relway.data

        rels = sa.select(h.c.child).where(h.c.parent == oid)\
                 .union(sa.select(oid))\
                 .scalar_subquery()

        ways, bbox = await get_way_elevation_data(conn, s.c.id, s.c.geom,
                                                  s.c.rels.overlap(sa.func.array(rels)),
                                                  step)

        if not ways:
            raise falcon.HTTPNotFound()

        ele = SegmentElevation(self.context.dem, bbox, max_segment_len=max_segment_len)
        for w in ways:
            ele.add_segment(step=step, **w)

        return ele.to_response(resp)
