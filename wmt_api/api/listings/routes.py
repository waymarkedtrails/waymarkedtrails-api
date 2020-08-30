# SPDX-License-Identifier: GPL-3.0-only
#
# This file is part of the Waymarked Trails Map Project
# Copyright (C) 2020 Sarah Hoffmann

import hug
from collections import OrderedDict

from ...common import directive
from ...common.types import bbox_type, ListOfIds
from ...output.route_list import RouteList
from ...output.route_item import RouteItem

import sqlalchemy as sa

hug.defaults.cli_output_format = hug.output_format.json

def _create_list(conn, sql, route, **kwargs):
    """ Enhance the given SQL term with ordering, send it to the database and
        format the results for JSON output.
    """
    res = RouteList(**kwargs)

    sql = sql.order_by(sa.desc(route.c.level), route.c.name)

    res.set_items(conn.execute(sql))

    return res


@hug.get()
@hug.cli()
def by_area(conn: directive.connection, tables: directive.tables,
            bbox: bbox_type, limit: hug.types.in_range(1, 100) = 20):
    """ Return the list of routes within the given area. `bbox` describes the
        area given, `limit` describes the maximum number of results.
    """
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
               .limit(limit)

    return _create_list(conn, sql, r, bbox=bbox)

@hug.get()
@hug.cli()
def by_ids(conn: directive.connection, tables: directive.tables,
           ids: ListOfIds()):
    """ Return route overview information by relation id.
    """
    r = tables.routes.data

    sql = sa.select(RouteItem.make_selectables(r))\
               .where(r.c.id.in_(ids))\
               .order_by(r.c.level, r.c.name)

    return _create_list(conn, sql, r, ids=ids)

@hug.get()
def search(query: hug.types.text, limit: hug.types.in_range(1, 100) = 20,
           page: hug.types.in_range(1, 10) = 1):
    """ Search a route by name.
    """
    return "TODO"

@hug.get()
def segments(bbox: bbox_type, ids: hug.types.delimited_list(',')):
    """ Return the geometry of the routes `ids` that intersect with the
        boundingbox `bbox`. If the route goes outside the box, the geometry
        is cut accordingly.
    """
    return "TODO"