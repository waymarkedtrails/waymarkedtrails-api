# SPDX-License-Identifier: GPL-3.0-only
#
# This file is part of the Waymarked Trails Map Project
# Copyright (C) 2020 Sarah Hoffmann

import hug
import sqlalchemy as sa

from ...common import directive
from ...common.formatter import format_as_redirect
from ...output.route_item import DetailedRouteItem, RouteItem
from ...output.wikilink import get_wikipedia_link

@hug.get('/')
@hug.cli()
def info(conn: directive.connection, tables: directive.tables,
         osmdata : directive.osmdata, oid : hug.types.number):
    "Return general information about the route."

    r = tables.routes.data
    o = osmdata.relation.data
    h = tables.hierarchy.data

    fields = DetailedRouteItem.make_selectables(r, o)

    res = DetailedRouteItem(conn.execute(sa.select(fields)
                            .where(r.c.id==oid)
                            .where(o.c.id==oid)).first())

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
def wikilink(conn: directive.connection, osmdata: directive.osmdata, oid):
    "Return a redirct into the Wikipedia page with further information."

    r = osmdata.relation.data

    return get_wikipedia_link(
             conn.scalar(sa.select([r.c.tags]).where(r.c.id == oid)),
             [])

@hug.get('/geometry/{geomtype}')
def geojson(oid, geomtype : hug.types.one_of(('geojson', 'kml', 'gpx'))):
    "Return the geometry of the function as geojson."
    return geomtype


@hug.get()
def elevation(oid):
    "Return the elevation profile of the route."
    return "TODO"
