# SPDX-License-Identifier: GPL-3.0-only
#
# This file is part of the Waymarked Trails Map Project
# Copyright (C) 2020-2023 Sarah Hoffmann
"""
Details API functions for guide posts.
"""

import hug
import sqlalchemy as sa

from ...common import directive
from ...output.node_item import NodeItem

@hug.get('/')
@hug.cli()
def info(conn: directive.connection, tables: directive.tables,
         osmdata: directive.osmdata, locale: directive.locale,
         oid: hug.types.number):
    "Return general information about the guide post."

    r = tables.guideposts.data
    o = osmdata.node.data

    sql = sa.select(*NodeItem.make_selectables(r, o))\
            .where(r.c.id == oid)\
            .join(o, o.c.id == r.c.id)

    res = conn.execute(sql).first()

    if res is None:
        raise hug.HTTPNotFound()

    return NodeItem('guidepost', oid).add_row_data(res, locale)
