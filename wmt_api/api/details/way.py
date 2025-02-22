# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of the Waymarked Trails Map Project
# Copyright (C) 2024 Sarah Hoffmann
import falcon
import sqlalchemy as sa
import geoalchemy2.functions as gf
from geoalchemy2 import Geography
from geoalchemy2.shape import to_shape

from ...common import params
from ...common.router import Router, needs_db
from ...common.errors import APIError
from ...common.json_writer import JsonWriter
from ...output.route_item import DetailedRouteItem
from ...output.wikilink import get_wikipedia_link
from ...output.geometry import RouteGeometry
from ...output.elevation import SegmentElevation, get_way_elevation_data

class APIDetailsWay(Router):

    def add_routes(self, app, base):
        base += '/{oid:int(min=1)}'
        app.add_route(base, self, suffix='info')
        app.add_route(base + '/wikilink', self, suffix='wikilink')
        app.add_route(base + '/geometry/{geomtype}', self, suffix='geometry')
        app.add_route(base + '/way-elevation', self, suffix='way_elevation')


    @needs_db
    async def on_get_info(self, conn, req, resp, oid):
        locale = params.get_locale(req)
        r = self.context.db.tables.ways.data

        sql = sa.select(*DetailedRouteItem.make_selectables(r)).where(r.c.id == oid)
        sql = sql.add_columns(sa.func.ST_Length(sa.cast(gf.ST_Transform(r.c.geom, 4326), Geography))
                                .label('way_length'),
                              r.c.geom.ST_AsGeoJSON().label('geom'))

        row = (await conn.execute(sql)).first()

        if row is None:
            raise falcon.HTTPNotFound()

        route_len = int(row.way_length)
        route_writer = JsonWriter()
        route_writer.start_object()\
            .keyval('route_type', 'route')\
            .keyval('length', route_len)\
            .keyval('linear', 'yes')\
            .keyval('start', 0)\
            .key('appendices').raw('[]').next()\
            .key('main').start_array().start_object()\
                .keyval('route_type', 'linear')\
                .keyval('length', route_len)\
                .keyval('linear', 'yes')\
                .keyval('start', 0)\
                .key('ways').start_array().start_object()\
                    .keyval('route_type', 'base')\
                    .keyval('id', row.id)\
                    .keyval('length', route_len)\
                    .keyval('start', 0)\
                    .keyval('tags', row.tags)\
                    .keyval('direction', 0)\
                    .keyval('role', '')\
                    .key('geometry').raw(row.geom).next()\
                .end_object().next().end_array()\
            .end_object().next().end_array()\
        .end_object()

        writer = JsonWriter()
        DetailedRouteItem(writer, row, locale, objtype='way',
                          route=route_writer(), linear='yes').finish()
        writer.to_response(resp)


    @needs_db
    async def on_get_wikilink(self, conn, req, resp, oid):
        locale = params.get_locale(req)

        r = self.context.db.osmdata.way.data

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

        r = self.context.db.tables.ways.data

        geom = r.c.geom
        if simplify > 0:
            geom = geom.ST_Simplify(r.c.geom.ST_NPoints()/int(simplify))
        if geomtype == 'geojson':
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

        s = self.context.db.tables.ways.data

        ways, bbox = await get_way_elevation_data(conn, s.c.id, s.c.geom,
                                                  s.c.id == oid, step)

        if not ways:
            raise falcon.HTTPNotFound()

        ele = SegmentElevation(self.context.dem, bbox, max_segment_len=max_segment_len)
        for w in ways:
            ele.add_segment(step=step, **w)

        return ele.to_response(resp)
