# SPDX-License-Identifier: GPL-3.0-only
#
# This file is part of the Waymarked Trails Map Project
# Copyright (C) 2020 Sarah Hoffmann

import hug
from collections import OrderedDict

from ...common import directive
from ...common.types import bbox_type, route_id_list
from ...common.formatter import format_as_geojson
from ...output.route_list import RouteList
from ...output.route_item import RouteItem

import sqlalchemy as sa

@hug.get()
@hug.cli()
def by_area(conn: directive.connection, tables: directive.tables,
            locale: directive.locale,
            bbox: bbox_type, limit: hug.types.in_range(1, 100) = 20):
    """ Return the list of routes within the given area. `bbox` describes the
        area given, `limit` describes the maximum number of results.
    """
    res = RouteList(bbox=bbox)

    r = tables.routes.data
    s = tables.segments.data
    h = tables.hierarchy.data

    rels = sa.select([sa.func.unnest(s.c.rels).label('rel')], distinct=True)\
                .where(s.c.geom.ST_Intersects(bbox.as_sql())).alias()

    sql = sa.select(RouteItem.make_selectables(r))\
               .where(r.c.top)\
               .where(sa.or_(r.c.id.in_(sa.select([h.c.parent], distinct=True)
                                   .where(h.c.child == rels.c.rel)),
                             r.c.id.in_(rels)
                     ))\
               .limit(limit)\
               .order_by(sa.desc(r.c.level), r.c.name)

    res.set_items(conn.execute(sql), locale)

    return res

@hug.get()
@hug.cli()
def by_ids(conn: directive.connection, tables: directive.tables,
           locale: directive.locale, relations: route_id_list):
    """ Return route overview information by relation id.
    """
    res = RouteList(relations=relations)

    r = tables.routes.data

    sql = sa.select(RouteItem.make_selectables(r))\
            .where(r.c.id.in_(relations))\
            .order_by(sa.desc(r.c.level), r.c.name)

    res.set_items(conn.execute(sql), locale)

    return res

@hug.get()
@hug.cli()
def search(conn: directive.connection, tables: directive.tables,
           locale: directive.locale,
           query: hug.types.text, limit: hug.types.in_range(1, 100) = 20,
           page: hug.types.in_range(1, 10) = 1):
    """ Search a route by name. `query` contains the string to search for.
        _limit_ ist the maximum number of results to return. _page_ the batch
        number of results to return, i.e. the requests returns results
        `[(page - 1) * limit, page * limit[`.
    """
    maxresults = page * limit

    res = RouteList(query=query, page=page)

    r = tables.routes.data
    base = sa.select(RouteItem.make_selectables(r))

    # First try: exact match of ref
    sql = base.where(sa.func.lower(r.c.ref) == query.lower()).limit(maxresults+1)
    res.set_items(conn.execute(sql), locale)

    # If that did not work and the search term is a number, maybe a relation
    # number?
    if len(res) == 0 and len(query) > 3 and query.isdigit():
        sql = base.where(r.c.id == int(query))
        res.set_items(conn.execute(sql), locale)
        if len(res) > 0:
            return res

    # Second try: fuzzy matching of text
    if len(res) <= maxresults:
        sim = sa.func.similarity(r.c.name, query)
        sql = base.column(sim.label('sim'))\
                  .order_by(sa.desc(sim))\
                  .limit(maxresults - len(res)) \
                  .where(sim > (0.5 if len(res) > 0 else 0.1))

        maxsim = None
        for o in conn.execute(sql):
            if maxsim is None:
                maxsim = o['sim']
            elif maxsim > o['sim'] * 3:
                break
            res.add_item(o, locale)

    if page > 1:
        res.drop_leading_results((page - 1) * limit)

    return res


@hug.get(output=format_as_geojson)
@hug.cli(output=format_as_geojson)
def segments(conn: directive.connection, tables: directive.tables,
             bbox: bbox_type, relations: route_id_list):
    """ Return the geometry of the routes `ids` that intersect with the
        boundingbox `bbox`. If the route goes outside the box, the geometry
        is cut accordingly.
    """

    r = tables.routes.data

    sql = sa.select([r.c.id, r.c.geom.ST_Intersection(bbox.as_sql()).label('geometry')])\
              .where(r.c.id.in_(relations)).alias()

    sql = sa.select([sa.literal("relation").label('type'),
                     sql.c.id, sql.c.geometry.ST_AsGeoJSON().label('geometry')])\
            .where(sa.not_(sa.func.ST_IsEmpty(sql.c.geometry)))

    return conn.execute(sql)
