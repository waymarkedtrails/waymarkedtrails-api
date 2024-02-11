# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of the Waymarked Trails Map Project
# Copyright (C) 2024 Sarah Hoffmann
import falcon
import sqlalchemy as sa
import geoalchemy2.functions as gf
from geoalchemy2.shape import to_shape

from ...common import params
from ...common.router import Router, needs_db
from ...common.errors import APIError
from ...common.json_writer import JsonWriter
from ...output.route_item import DetailedRouteItem
from ...output.wikilink import get_wikipedia_link
from ...output.geometry import RouteGeometry
from ...output.elevation import RouteElevation

class APIDetailsWay(Router):

    def add_routes(self, app, base):
        base += '/{oid:int(min=1)}'
        app.add_route(base, self, suffix='info')
        app.add_route(base + '/wikilink', self, suffix='wikilink')
        app.add_route(base + '/geometry/{geomtype}', self, suffix='geometry')
        app.add_route(base + '/elevation', self, suffix='elevation')


    @needs_db
    async def on_get_info(self, conn, req, resp, oid):
        locale = params.get_locale(req)
        r = self.context.db.tables.ways.data
        o = self.context.db.osmdata.way.data

        sql = sa.select(*DetailedRouteItem.make_selectables(r, o))\
                                .where(r.c.id == oid)\
                                .join(o, o.c.id == r.c.id)

        row = (await conn.execute(sql)).first()

        if row is None:
            raise falcon.HTTPNotFound()

        writer = JsonWriter()
        DetailedRouteItem(writer, row, locale, objtype='way').finish()
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
    async def on_get_elevation(self, conn, req, resp, oid):
        segments = params.as_int(req, 'segments', default=100, vmin=1, vmax=500)

        if self.context.dem is None:
            raise falcon.HTTPNotFound()

        r = self.context.db.tables.ways.data

        sel = sa.select(gf.ST_Points(gf.ST_Collect(
                             gf.ST_PointN(r.c.geom, 1),
                             gf.ST_LineInterpolatePoints(r.c.geom, 1.0/segments))),
                        sa.func.ST_Length2dSpheroid(gf.ST_Transform(r.c.geom, 4326),
                               sa.text('\'SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]]\''))
                       ).where(r.c.id == oid)

        res = (await conn.execute(sel)).first()

        if res is None:
            raise falcon.HTTPNotFound()

        geom = to_shape(res[0])
        ele = RouteElevation(oid, self.context.dem, geom.bounds)

        xcoord, ycoord = zip(*((p.x, p.y) for p in geom.geoms))
        geomlen = res[1]
        pos = [geomlen*i/float(segments) for i in range(segments + 1)]

        ele.add_segment(xcoord, ycoord, pos)

        ele.to_response(resp)
