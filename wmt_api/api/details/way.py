# SPDX-License-Identifier: GPL-3.0-only
#
# This file is part of the Waymarked Trails Map Project
# Copyright (C) 2020 Sarah Hoffmann
"""
Details API functions for simple ways (from the way table).
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

    sql = sa.select(DetailedRouteItem.make_selectables(r, o))\
                            .where(r.c.id==oid)\
                            .where(o.c.id==oid)

    row = conn.execute(sql).first()

    if row is None:
        raise hug.HTTPNotFound()

    return DetailedRouteItem(row, locale)


@hug.get('/wikilink', output=format_as_redirect)
@hug.cli(output=hug.output_format.text)
def wikilink(conn: directive.connection, osmdata: directive.osmdata,
             locale: directive.locale, oid: hug.types.number):
    "Return a redirct into the Wikipedia page with further information."

    r = osmdata.way.data

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
    """ Return the geometry of the way. Supported formats are geojson,
        kml and gpx.
    """
    r = tables.ways.data

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
              cfg: directive.api_config,
              oid: hug.types.number, segments: hug.types.in_range(1, 500) = 100):
    "Return the elevation profile of the way."

    r = tables.ways.data

    gen = sa.select([sa.func.generate_series(0, segments).label('i')]).alias()
    field = gf.ST_LineInterpolatePoint(r.c.geom, gen.c.i/float(segments))
    field = gf.ST_Collect(field)

    sel = sa.select([field]).where(r.c.id == oid)

    res = conn.scalar(sel)

    if res is None:
        raise hug.HTTPNotFound()

    geom = to_shape(res)
    ele = RouteElevation(oid, cfg.DEM_FILE, geom.bounds)

    xcoord, ycoord = zip(*((p.x, p.y) for p in geom))
    geomlen = LineString(geom).length
    pos = [geomlen*i/float(segments) for i in range(segments)]

    ele.add_segment(xcoord, ycoord, pos)

    return ele.as_dict()
