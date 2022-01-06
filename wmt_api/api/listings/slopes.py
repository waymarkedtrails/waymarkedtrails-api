# SPDX-License-Identifier: GPL-3.0-only
#
# This file is part of the Waymarked Trails Map Project
# Copyright (C) 2022 Sarah Hoffmann

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

    sels = RouteItem.make_selectables(r)
    sels.append(sa.literal('relation').label('type'))
    sql = sa.select(sels)\
               .where(r.c.top)\
               .where(sa.or_(r.c.id.in_(sa.select([h.c.parent], distinct=True)
                                   .where(h.c.child == rels.c.rel)),
                             r.c.id.in_(rels)
                     ))\
               .limit(limit)\
               .order_by(sa.desc(r.c.piste), r.c.name)

    res.set_items(conn.execute(sql), locale)

    if len(res) >= limit:
        return res

    w = tables.ways.data
    ws = tables.joined_ways.data
    sql = sa.select([sa.func.coalesce(ws.c.id, w.c.id).label('id'),
                     sa.case([(ws.c.id == None, 'way')], else_='wayset').label('type'),
                     w.c.name, w.c.intnames, w.c.symbol,
                     w.c.piste], distinct=True)\
            .select_from(w.outerjoin(ws, w.c.id == ws.c.child))\
            .where(w.c.geom.ST_Intersects(bbox.as_sql()))\
            .order_by(w.c.name)\
            .limit(limit - len(res))

    res.add_items(conn.execute(sql), locale)

    return res

@hug.get()
@hug.cli()
def by_ids(conn: directive.connection, tables: directive.tables,
           locale: directive.locale,
           relations: route_id_list = [], ways: route_id_list = [],
           waysets: route_id_list = []):
    """ Return route overview information by relation id.
    """
    res = RouteList(relations=relations, ways=ways, waysets=waysets)

    if relations:
        r = tables.routes.data

        sels = RouteItem.make_selectables(r)
        sels.append(sa.literal('relation').label('type'))

        sql = sa.select(sels).where(r.c.id.in_(relations))

        res.add_items(conn.execute(sql), locale)

    if ways:
        w = tables.ways.data

        sels = RouteItem.make_selectables(w)
        sels.append(sa.literal('way').label('type'))

        sql = sa.select(sels).where(w.c.id.in_(ways))

        res.add_items(conn.execute(sql), locale)

    if waysets:
        w = tables.ways.data

        sels = RouteItem.make_selectables(w)
        sels.append(sa.literal('wayset').label('type'))

        sql = sa.select(sels).where(w.c.id.in_(waysets))

        res.add_items(conn.execute(sql), locale)

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

    r = tables.routes.data
    sels = RouteItem.make_selectables(r)
    sels.append(sa.literal('relation').label('type'))
    rbase = sa.select(sels)

    w = tables.ways.data
    ws = tables.joined_ways.data
    wbase = sa.select([sa.func.coalesce(ws.c.id, w.c.id).label('id'),
                         sa.case([(ws.c.id == None, 'way')], else_='wayset').label('type'),
                         w.c.name, w.c.intnames, w.c.symbol,
                         w.c.piste], distinct=True)\
              .select_from(w.outerjoin(ws, w.c.id == ws.c.child))

    todos = ((r, rbase), (w, wbase))

    objs = RouteList(query=query, page=page)

    # First try: exact match of ref
    for t, base in todos:
        if len(objs) <= maxresults:
            refmatch = base.where(t.c.name == '[%s]' % query).limit(maxresults - len(objs) + 1)
            objs.add_items(conn.execute(refmatch), locale)

    # If that did not work and the search term is a number, maybe a relation
    # number?
    if not objs and len(query) > 3 and query.isdigit():
        for t, base in todos:
            idmatch = base.where(t.c.id == int(query))
            objs.add_items(conn.execute(idmatch), locale)

        if objs:
            return objs

    # Second try: fuzzy matching of text
    for t, base in todos:
        if len(objs) <= maxresults:
            sim = sa.func.similarity(t.c.name, query)
            res = base.add_columns(sim.label('sim'))\
                    .where(t.c.name.notlike('(%'))\
                    .order_by(sa.desc(sim))\
                    .limit(maxresults - len(objs) + 1)
            if objs:
                res = res.where(sim > 0.5)
            else:
                res = res.where(sim > 0.1)

            maxsim = None
            for r in conn.execute(res):
                if maxsim is None:
                    maxsim = r['sim']
                elif maxsim > r['sim'] * 3:
                    break
                objs.add_item(r, locale)

    return objs


@hug.get(output=format_as_geojson)
@hug.cli(output=format_as_geojson)
def segments(conn: directive.connection, tables: directive.tables,
             bbox: bbox_type, relations: route_id_list = None,
             ways: route_id_list = None, waysets: route_id_list = None):
    """ Return the geometry of the routes `ids` that intersect with the
        boundingbox `bbox`. If the route goes outside the box, the geometry
        is cut accordingly.
    """
    objs = []

    if relations:
        r = tables.routes.data
        sql = sa.select([sa.literal("relation").label('type'), r.c.id,
                         r.c.geom.ST_Intersection(bbox.as_sql()).label('geometry')])\
                .where(r.c.id.in_(relations)).alias()

        sql = sa.select([sql.c.type, sql.c.id, sql.c.geometry.ST_AsGeoJSON().label('geometry')])\
                .where(sa.not_(sa.func.ST_IsEmpty(sql.c.geometry)))

        for x in conn.execute(sql):
            objs.append(x)

    if ways:
        w = tables.ways.data
        sql = sa.select([sa.literal("way").label('type'), w.c.id,
                         w.c.geom.ST_Intersection(bbox.as_sql()).label('geometry')])\
                .where(w.c.id.in_(ways)).alias()

        sql = sa.select([sql.c.type, sql.c.id, sql.c.geometry.ST_AsGeoJSON().label('geometry')])\
                .where(sa.not_(sa.func.ST_IsEmpty(sql.c.geometry)))

        for x in conn.execute(sql):
            objs.append(x)

    if waysets:
        ws = tables.joined_ways.data
        sql = sa.select([sa.literal("wayset").label('type'),
                         ws.c.id.label('id'),
                         sa.func.ST_CollectionHomogenize(
                             sa.func.ST_Collect(w.c.geom.ST_Intersection(bbox.as_sql()))).label('geometry')
                        ])\
                .select_from(w.join(ws, w.c.id == ws.c.child))\
                .where(ws.c.id.in_(waysets)).group_by(ws.c.id).alias()

        sql = sa.select([sql.c.type, sql.c.id, sql.c.geometry.ST_AsGeoJSON().label('geometry')])\
                .where(sa.not_(sa.func.ST_IsEmpty(sql.c.geometry)))

        for x in conn.execute(sql):
            objs.append(x)

    return objs

