# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of the Waymarked Trails Map Project
# Copyright (C) 2024 Sarah Hoffmann
import falcon
import sqlalchemy as sa
import geoalchemy2.functions as gf
from geoalchemy2.shape import to_shape
from shapely.geometry import Point, LineString

from ...common import params
from ...common.errors import APIError
from ...common.json_writer import JsonWriter
from ...common.router import Router, needs_db
from ...output.wikilink import get_wikipedia_link
from ...output.route_item import DetailedRouteItem, RouteItem
from ...output.geometry import RouteGeometry
from ...output.elevation import RouteElevation


class APIDetailsRelation(Router):

    def add_routes(self, app, base):
        base += '/{oid:int(min=1)}'
        app.add_route(base, self, suffix='info')
        app.add_route(base + '/wikilink', self, suffix='wikilink')
        app.add_route(base + '/geometry/{geomtype}', self, suffix='geometry')
        app.add_route(base + '/elevation', self, suffix='elevation')


    @needs_db
    async def on_get_info(self, conn, req, resp, oid):
        locale = params.get_locale(req)

        r = self.context.db.tables.routes.data
        o = self.context.db.osmdata.relation.data
        h = self.context.db.tables.hierarchy.data

        fields = DetailedRouteItem.make_selectables(r, o)
        fields.append(sa.func.jsonb_path_query_array(o.c.members,
                                          sa.text("'$[*] ? (@.type == \"R\").id'"))
                        .label("relation_ids"))

        row = (await conn.execute(sa.select(*fields)
                                    .where(r.c.id == oid)
                                    .join(o, o.c.id == r.c.id))).first()

        if row is None:
            raise falcon.HTTPNotFound()

        writer = JsonWriter()
        res = DetailedRouteItem(writer, row, locale, objtype='relation')

        # add subroutes where applicable
        if row.relation_ids:
            sections = await conn.execute(sa.select(*RouteItem.make_selectables(r))\
                                            .where(r.c.id.in_(row.relation_ids)))

            # Make sure subroutes appear in the order of the relation.
            subs = { s.id: s for s in sections}
            res.add_extra_route_info('subroutes',
                                     (subs[oid] for oid in row.relation_ids if oid in subs),
                                     locale)


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
    async def on_get_elevation(self, conn, req, resp, oid):
        segments = params.as_int(req, 'segments', default=100, vmin=1, vmax=500)

        if self.context.dem is None:
            raise falcon.HTTPNotFound()

        r = self.context.db.tables.routes.data

        sel = sa.select(gf.ST_Points(gf.ST_Collect(
                             gf.ST_PointN(r.c.geom, 1),
                             gf.ST_LineInterpolatePoints(r.c.geom, 1.0/segments))),
                        sa.func.ST_Length2dSpheroid(gf.ST_Transform(r.c.geom, 4326),
                               sa.text('\'SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]]\''))
                        ).where(r.c.id == oid)\
                .where(r.c.geom.ST_GeometryType() == 'ST_LineString')

        res = (await conn.execute(sel)).first()

        if res is not None:
            geom = to_shape(res[0])
            ele = RouteElevation(oid, self.context.dem, geom.bounds)

            xcoord, ycoord = zip(*((p.x, p.y) for p in geom.geoms))
            geomlen = res[1]
            pos = [geomlen*i/float(segments) for i in range(segments + 1)]

            ele.add_segment(xcoord, ycoord, pos)

            return ele.to_response(resp)

        # special treatment for multilinestrings
        sel = sa.select(r.c.geom,
                        sa.literal_column("""ST_Length2dSpheroid(ST_MakeLine(ARRAY[ST_Points(ST_Transform(geom,4326))]),
                                 'SPHEROID[\"WGS 84\",6378137,298.257223563,AUTHORITY["EPSG",\"7030\"]]')"""),
                        r.c.geom.ST_NPoints(),
                        gf.ST_Length(r.c.geom))\
                    .where(r.c.id == oid)

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

        prev = None
        for seg in geom.geoms:
            p = seg.coords[0]
            xcoords = [p[0]]
            ycoords = [p[1]]
            pos = []
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

        return ele.to_response(resp)
