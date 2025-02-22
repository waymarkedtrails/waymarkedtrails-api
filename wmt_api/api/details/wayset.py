# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of the Waymarked Trails Map Project
# Copyright (C) 2024 Sarah Hoffmann
from array import array

import falcon
import sqlalchemy as sa
import geoalchemy2.functions as gf
from geoalchemy2.shape import to_shape
from geoalchemy2 import Geography
from shapely.geometry import Point, LineString

from ...common import params
from ...common.router import Router, needs_db
from ...common.errors import APIError
from ...common.json_writer import JsonWriter
from ...output.route_item import DetailedRouteItem
from ...output.wikilink import get_wikipedia_link
from ...output.geometry import RouteGeometry
from ...output.elevation import SegmentElevation, get_way_elevation_data

class APIDetailsWayset(Router):

    def add_routes(self, app, base):
        base += '/{oid:int(min=1)}'
        app.add_route(base, self, suffix='info')
        app.add_route(base + '/wikilink', self, suffix='wikilink')
        app.add_route(base + '/geometry/{geomtype}', self, suffix='geometry')
        app.add_route(base + '/way-elevation', self, suffix='way_elevation')


    @needs_db
    async def on_get_info(self, conn, req, resp, oid):
        locale = params.get_locale(req)

        w = self.context.db.tables.ways.data
        ws = self.context.db.tables.joined_ways.data

        # first get the information to create the route
        sql = sa.select(w.c.id, w.c.tags,
                        sa.func.ST_Length(sa.cast(gf.ST_Transform(w.c.geom, 4326), Geography))
                               .label('length'),
                        w.c.geom.ST_AsGeoJSON().label('geom'))\
                .join(ws, ws.c.child == w.c.id)\
                .where(ws.c.id == oid)

        ways_writer = JsonWriter()
        ways_writer.start_array()
        total_length = 0

        for row in await conn.execute(sql):
            ways_writer.start_object()\
                .keyval('route_type', 'linear')\
                .keyval('length', int(row.length))\
                .keyval('start', 0)\
                .key('ways').start_array().start_object()\
                    .keyval('route_type', 'base')\
                    .keyval('id', row.id)\
                    .keyval('length', int(row.length))\
                    .keyval('start', total_length)\
                    .keyval('tags', row.tags)\
                    .keyval('direction', 0)\
                    .keyval('role', '')\
                    .key('geometry').raw(row.geom).next()\
                    .end_object().next()\
                .end_array().end_object().next()
            total_length += int(row.length)

        ways_writer.end_array()

        if total_length == 0:
            raise falcon.HTTPNotFound()

        # then get the information about the way set
        w2 = self.context.db.tables.ways.data.alias()
        geom = sa.select(ws.c.id, gf.ST_Collect(w2.c.geom).label('geom'))\
                 .join(w2, ws.c.child == w2.c.id)\
                 .group_by(ws.c.id)\
                 .subquery()
        sql = sa.select(w.c.id, w.c.name, w.c.intnames, w.c.symbol, w.c.ref,
                        w.c.piste, w.c.tags,
                        geom.c.geom.ST_Envelope().label('bbox'))\
                 .join(geom, geom.c.id == oid)\
                 .where(w.c.id == oid)

        row = (await conn.execute(sql)).first()

        if row is None:
            raise falcon.HTTPNotFound()

        route_writer = JsonWriter()
        route_writer.start_object()\
            .keyval('route_type', 'route')\
            .keyval('length', total_length)\
            .keyval('linear', 'no')\
            .keyval('start', 0)\
            .key('appendices').raw('[]').next()\
            .key('main').raw(ways_writer()).next()\
        .end_object()

        writer = JsonWriter()
        DetailedRouteItem(writer, row, locale, objtype='wayset',
                          linear='no', route=route_writer()).finish()
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


        w = self.context.db.tables.ways.data
        ws = self.context.db.tables.joined_ways.data

        geom = gf.ST_LineMerge(gf.ST_Collect(w.c.geom))

        if simplify > 0:
            geom = geom.ST_Simplify(gf.ST_Collect(w.c.geom).ST_NPoints()/int(simplify))

        if geomtype == 'geojson' :
            geom = geom.ST_AsGeoJSON()
        else:
            geom = geom.ST_Transform(4326)

        sql = sa.select(w.c.name, w.c.intnames, w.c.ref, ws.c.id, geom.label('geom'))\
                .join(ws, w.c.id == ws.c.child)\
                .where(ws.c.id == oid)\
                .group_by(w.c.name, w.c.intnames, w.c.ref, ws.c.id)

        obj = (await conn.execute(sql)).first()

        if obj is None:
            raise falcon.HTTPNotFound()

        RouteGeometry(obj, locales=locale, fmt=geomtype).to_response(req, resp)


    @needs_db
    async def on_get_way_elevation(self, conn, req, resp, oid):
        max_segment_len = params.as_int(req, 'simplify',  default=0, vmin=2)
        step = max(max_segment_len/10, min(max_segment_len, 50))

        if self.context.dem is None:
            raise falcon.HTTPRouteNotFound()

        w = self.context.db.tables.ways.data
        ws = self.context.db.tables.joined_ways.data

        ways, bbox = await get_way_elevation_data(conn, w.c.id, w.c.geom,
                                                  sa.and_(w.c.id == ws.c.child,
                                                          ws.c.id == oid),
                                                  step)

        if not ways:
            raise falcon.HTTPNotFound()

        ele = SegmentElevation(self.context.dem, bbox, max_segment_len=max_segment_len)
        for way in ways:
            ele.add_segment(step=step, **way)

        return ele.to_response(resp)
