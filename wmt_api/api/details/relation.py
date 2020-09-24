# SPDX-License-Identifier: GPL-3.0-only
#
# This file is part of the Waymarked Trails Map Project
# Copyright (C) 2020 Sarah Hoffmann

import hug
import sqlalchemy as sa

from ...common import directive
from ...common.formatter import format_as_redirect, format_object
from ...output.route_item import DetailedRouteItem, RouteItem
from ...output.wikilink import get_wikipedia_link
from ...output.geometry import RouteGeometry

@hug.get('/')
@hug.cli()
def info(conn: directive.connection, tables: directive.tables,
         osmdata : directive.osmdata, locale: directive.locale,
         oid : hug.types.number):
    "Return general information about the route."

    r = tables.routes.data
    o = osmdata.relation.data
    h = tables.hierarchy.data

    sql = sa.select(DetailedRouteItem.make_selectables(r, o))\
                            .where(r.c.id==oid)\
                            .where(o.c.id==oid)

    res = DetailedRouteItem(conn.execute(sql).first(), locale)

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

@hug.get(output=format_as_redirect)
@hug.cli(output=hug.output_format.text)
def wikilink(conn: directive.connection, osmdata: directive.osmdata,
             locale: directive.locale, oid):
    "Return a redirct into the Wikipedia page with further information."

    r = osmdata.relation.data

    return get_wikipedia_link(
             conn.scalar(sa.select([r.c.tags]).where(r.c.id == oid)),
             locale)

@hug.get('/geometry/{geomtype}', output=format_object)
@hug.cli(output=format_object)
def geometry(conn: directive.connection, tables: directive.tables,
             locale: directive.locale,
             oid, geomtype : hug.types.one_of(('geojson', 'kml', 'gpx')),
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
        return hug.HTTPNotFound()

    return RouteGeometry(obj, locales=locale, fmt=geomtype)


@hug.get()
def elevation(oid):
    "Return the elevation profile of the route."
    return "TODO"
