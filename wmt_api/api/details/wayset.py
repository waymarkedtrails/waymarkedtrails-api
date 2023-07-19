# SPDX-License-Identifier: GPL-3.0-only
#
# This file is part of the Waymarked Trails Map Project
# Copyright (C) 2020-2023 Sarah Hoffmann
"""
Details API functions for joined ways (from the way table).
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
    "Return general information about the way."

    r = tables.ways.data
    o = osmdata.way.data
    ws = tables.joined_ways.data

    w = tables.ways.data
    geom = sa.select(gf.ST_Collect(w.c.geom).label('geom'))\
             .join(ws, w.c.id == ws.c.child)\
             .where(ws.c.id == oid)\
             .alias()

    fields = [r.c.id, r.c.name, r.c.intnames, r.c.symbol, r.c.ref,
              r.c.piste, o.c.tags, geom]

    sql = sa.select(*fields)\
            .where(r.c.id == oid)\
            .join(o, o.c.id == r.c.id)\
            .subquery()

    outer = sa.select(sql,
                      sa.func.ST_Length2dSpheroid(gf.ST_Transform(sql.c.geom, 4326),
                           'SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]]').label("length"),
                      sql.c.geom.ST_Envelope().label('bbox'))

    row = conn.execute(outer).first()

    if row is None:
        raise hug.HTTPNotFound()

    return DetailedRouteItem(row, locale, objtype='wayset')


@hug.get('/wikilink', output=format_as_redirect)
@hug.cli(output=hug.output_format.text)
def wikilink(conn: directive.connection, osmdata: directive.osmdata,
             locale: directive.locale, oid: hug.types.number):
    "Return a redirct into the Wikipedia page with further information."

    r = osmdata.way.data

    return get_wikipedia_link(
             conn.scalar(sa.select(r.c.tags).where(r.c.id == oid)),
             locale)

@hug.get('/geometry/{geomtype}', output=format_object)
@hug.cli(output=format_object)
def geometry(conn: directive.connection, tables: directive.tables,
             locale: directive.locale,
             oid: hug.types.number,
             geomtype : hug.types.one_of(('geojson', 'kml', 'gpx')),
             simplify : int = None):
    """ Return the geometry of the way. Supported formats are geojson,
        kml and gpx.
    """
    w = tables.ways.data
    ws = tables.joined_ways.data

    geom = gf.ST_LineMerge(gf.ST_Collect(w.c.geom))

    if simplify is not None:
        geom = geom.ST_Simplify(r.c.geom.ST_NPoints()/int(simplify))

    if geomtype == 'geojson' :
        geom = geom.ST_AsGeoJSON()
    else:
        geom = geom.ST_Transform(4326)

    sql = sa.select(w.c.name, w.c.intnames, w.c.ref, ws.c.id, geom.label('geom'))\
            .where(w.c.id == ws.c.child)\
            .where(ws.c.id == oid)\
            .group_by(w.c.name, w.c.intnames, w.c.ref, ws.c.id)

    obj = conn.execute(sql).first()

    if obj is None:
        raise hug.HTTPNotFound()

    return RouteGeometry(obj, locales=locale, fmt=geomtype)


@hug.get()
@hug.cli()
def elevation(conn: directive.connection, tables: directive.tables,
              dem: directive.dem_file,
              oid: hug.types.number, segments: hug.types.in_range(1, 500) = 100):
    "Return the elevation profile of the way."

    if dem is None:
        raise hug.HTTPNotFound()

    w = tables.ways.data
    ws = tables.joined_ways.data

    sql = sa.select(gf.ST_LineMerge(gf.ST_Collect(w.c.geom)).label('geom'))\
            .where(w.c.id == ws.c.child)\
            .where(ws.c.id == oid)\
            .alias()

    sel = sa.select(sql.c.geom,
                    sa.literal_column("""ST_Length2dSpheroid(ST_MakeLine(ARRAY[ST_Points(ST_Transform(geom,4326))]),
                            'SPHEROID[\"WGS 84\",6378137,298.257223563,AUTHORITY["EPSG",\"7030\"]]')"""),
                    sql.c.geom.ST_NPoints(),
                    gf.ST_Length(sql.c.geom))

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

    return ele.as_dict()
