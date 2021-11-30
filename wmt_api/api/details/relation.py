# SPDX-License-Identifier: GPL-3.0-only
#
# This file is part of the Waymarked Trails Map Project
# Copyright (C) 2020 Sarah Hoffmann
"""
Details API functions for route relations (from the route table).
"""
from array import array

import hug
import sqlalchemy as sa
import geoalchemy2.functions as gf
from geoalchemy2.shape import to_shape
from shapely.geometry import Point, LineString

from ...common import directive
from ...common.formatter import format_as_redirect, format_object
from ...output.route_item import DetailedRouteItem, RouteItem
from ...output.wikilink import get_wikipedia_link
from ...output.geometry import RouteGeometry
from ...output.elevation import RouteElevation

@hug.get('/')
@hug.cli()
def info(conn: directive.connection, tables: directive.tables,
         osmdata: directive.osmdata, locale: directive.locale,
         oid: hug.types.number):
    "Return general information about the route."

    r = tables.routes.data
    o = osmdata.relation.data
    h = tables.hierarchy.data

    sql = sa.select(DetailedRouteItem.make_selectables(r, o))\
                            .where(r.c.id==oid)\
                            .where(o.c.id==oid)

    row = conn.execute(sql).first()

    if row is None:
        raise hug.HTTPNotFound()

    res = DetailedRouteItem(row, locale, objtype='relation')

    # add hierarchy where applicable
    for rtype in ('subroutes', 'superroutes'):
        if rtype == 'subroutes':
            w = sa.select([h.c.child], distinct=True)\
                    .where(h.c.parent == oid).where(h.c.depth == 2)
        else:
            w = sa.select([h.c.parent], distinct=True)\
                     .where(h.c.child == oid).where(h.c.depth == 2)

        sections = conn.execute(sa.select(RouteItem.make_selectables(r))\
                                 .where(r.c.id != oid).where(r.c.id.in_(w)))

        if sections.rowcount > 0:
            res.add_extra_info(rtype, [RouteItem(s) for s in sections])

    return res

@hug.get('/wikilink', output=format_as_redirect)
@hug.cli(output=hug.output_format.text)
def wikilink(conn: directive.connection, osmdata: directive.osmdata,
             locale: directive.locale, oid: hug.types.number):
    "Return a redirct into the Wikipedia page with further information."

    r = osmdata.relation.data

    return get_wikipedia_link(
             conn.scalar(sa.select([r.c.tags]).where(r.c.id == oid)),
             locale)

@hug.get('/geometry/{geomtype}', output=format_object)
@hug.cli(output=format_object)
def geometry(conn: directive.connection, tables: directive.tables,
             locale: directive.locale,
             oid: hug.types.number,
             geomtype : hug.types.one_of(('geojson', 'kml', 'gpx')),
             simplify : int = None):
    """ Return the geometry of the function. Supported formats are geojson,
        kml and gpx.
    """
    r = tables.routes.data

    geom = r.c.geom
    if simplify is not None:
        geom = geom.ST_Simplify(r.c.geom.ST_NPoints()/int(simplify))
    if geomtype == 'geojson' :
        geom = geom.ST_AsGeoJSON()
    else:
        geom = geom.ST_Transform(4326)

    rows = [r.c.name, r.c.intnames, r.c.ref, r.c.id, geom.label('geom')]

    obj = conn.execute(sa.select(rows).where(r.c.id==oid)).first()

    if obj is None:
        raise hug.HTTPNotFound()

    return RouteGeometry(obj, locales=locale, fmt=geomtype)


@hug.get()
@hug.cli()
def elevation(conn: directive.connection, tables: directive.tables,
              dem: directive.dem_file,
              oid: hug.types.number, segments: hug.types.in_range(1, 500) = 100):
    "Return the elevation profile of the route."

    if dem is None:
        raise hug.HTTPNotFound()

    r = tables.routes.data

    sel = sa.select([gf.ST_Points(gf.ST_Collect(
                         gf.ST_PointN(r.c.geom, 1),
                         gf.ST_LineInterpolatePoints(r.c.geom, 1.0/segments))),
                     sa.func.ST_Length2dSpheroid(gf.ST_Transform(r.c.geom, 4326),
                           'SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]]')
                    ]).where(r.c.id == oid)\
            .where(r.c.geom.ST_GeometryType() == 'ST_LineString')

    res = conn.execute(sel).first()

    if res is not None:
        geom = to_shape(res[0])
        ele = RouteElevation(oid, dem, geom.bounds)

        xcoord, ycoord = zip(*((p.x, p.y) for p in geom))
        geomlen = res[1]
        pos = [geomlen*i/float(segments) for i in range(segments + 1)]

        ele.add_segment(xcoord, ycoord, pos)

        return ele.as_dict()

    # special treatment for multilinestrings
    sel = sa.select([r.c.geom,
                     sa.literal_column("""ST_Length2dSpheroid(ST_MakeLine(ARRAY[ST_Points(ST_Transform(geom,4326))]),
                             'SPHEROID[\"WGS 84\",6378137,298.257223563,AUTHORITY["EPSG",\"7030\"]]')"""),
                     r.c.geom.ST_NPoints(),
                     gf.ST_Length(r.c.geom)])\
                .where(r.c.id == oid)

    res = conn.execute(sel).first()

    if res is None or res[0] is None:
        raise hug.HTTPNotFound()

    geom = to_shape(res[0])
    # Computing length in Mercator is slightly off, correct it via the
    # actual length.
    dist_fac = res[1]/res[3]
    ele = RouteElevation(oid, dem, geom.bounds)

    if res[2] > 10000:
        geom = geom.simplify(res[2]/500, preserve_topology=False)
    elif res[2] > 4000:
        geom = geom.simplify(res[2]/1000, preserve_topology=False)

    prev = None
    for seg in geom:
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

    return ele.as_dict()
