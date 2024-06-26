# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of the Waymarked Trails Map Project
# Copyright (C) 2024 Sarah Hoffmann
from array import array

import falcon
import sqlalchemy as sa
import geoalchemy2.functions as gf
from geoalchemy2.shape import to_shape
from shapely.geometry import Point, LineString

from ...common import params
from ...common.router import Router, needs_db
from ...common.errors import APIError
from ...common.json_writer import JsonWriter
from ...output.route_item import DetailedRouteItem
from ...output.wikilink import get_wikipedia_link
from ...output.geometry import RouteGeometry
from ...output.elevation import RouteElevation

class APIDetailsWayset(Router):

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
        ws = self.context.db.tables.joined_ways.data
        w = self.context.db.tables.ways.data.alias()

        geom = sa.select(ws.c.id, gf.ST_Collect(w.c.geom).label('geom'))\
                 .join(w, ws.c.child == w.c.id)\
                 .group_by(ws.c.id)\
                 .subquery()

        fields = [r.c.id, r.c.name, r.c.intnames, r.c.symbol, r.c.ref,
                  r.c.piste, o.c.tags,
                  sa.func.ST_Length2dSpheroid(gf.ST_Transform(geom.c.geom, 4326),
                               sa.text('\'SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]]\'')).label("length"),
                          geom.c.geom.ST_Envelope().label('bbox')]

        sql = sa.select(*fields)\
                .join(o, o.c.id == r.c.id)\
                .join(geom, geom.c.id == oid)\
                .where(r.c.id == oid)

        row = (await conn.execute(sql)).first()

        if row is None:
            raise falcon.HTTPNotFound()

        writer = JsonWriter()
        DetailedRouteItem(writer, row, locale, objtype='wayset').finish()
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
    async def on_get_elevation(self, conn, req, resp, oid):
        segments = params.as_int(req, 'segments', default=100, vmin=1, vmax=500)

        if self.context.dem is None:
            raise falcon.HTTPNotFound()

        w = self.context.db.tables.ways.data
        ws = self.context.db.tables.joined_ways.data

        sql = sa.select(gf.ST_LineMerge(gf.ST_Collect(w.c.geom)).label('geom'))\
                .join(ws, w.c.id == ws.c.child)\
                .where(ws.c.id == oid)\
                .alias()

        sel = sa.select(sql.c.geom,
                        sa.literal_column("""ST_Length2dSpheroid(ST_MakeLine(ARRAY[ST_Points(ST_Transform(geom,4326))]),
                                'SPHEROID[\"WGS 84\",6378137,298.257223563,AUTHORITY["EPSG",\"7030\"]]')"""),
                        sql.c.geom.ST_NPoints(),
                        gf.ST_Length(sql.c.geom))

        res = (await conn.execute(sel)).first()

        if res is None or res[0] is None:
            raise falcon.HTTPNotFound()

        geom = to_shape(res[0])
        # Computing length in Mercator is slightly off, correct it via the
        # actual length.
        dist_fac = res[1]/res[3]

        ele = RouteElevation(oid, self.context.dem, geom.bounds)

        if res[2] > 10000:
            geom = geom.simplify(res[2]/500, preserve_topology=False)
        elif res[2] > 4000:
            geom = geom.simplify(res[2]/1000, preserve_topology=False)

        if geom.geom_type == 'LineString':
            geom_list = [geom]
        else:
            geom_list = geom.geoms

        prev = None
        for seg in geom_list:
            p = seg.coords[0]
            xcoords = array('d', [p[0]])
            ycoords = array('d', [p[1]])
            pos = array('d')
            if prev is not None:
                pos.append(prev[2][-1] + \
                        Point(prev[0][-1], prev[1][-1]).distance(Point(*p)) * dist_fac)
            else:
                pos.append(0.0)
            for p in seg.coords[1:]:
                pos.append(pos[-1] + Point(xcoords[-1], ycoords[-1]).distance(Point(*p)) * dist_fac)
                xcoords.append(p[0])
                ycoords.append(p[1])

            ele.add_segment(xcoords, ycoords, pos)
            prev = (xcoords, ycoords, pos)

        ele.to_response(resp)

