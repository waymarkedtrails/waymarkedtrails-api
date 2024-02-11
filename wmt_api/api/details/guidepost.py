# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of the Waymarked Trails Map Project
# Copyright (C) 2024 Sarah Hoffmann
import falcon
import sqlalchemy as sa

from ...common import params
from ...common.router import Router, needs_db
from ...output.node_item import NodeItem

class APIDetailsGuidepost(Router):

    def add_routes(self, app, base):
        base += '/{oid:int(min=1)}'
        app.add_route(base, self, suffix='info')


    @needs_db
    async def on_get_info(self, conn, req, resp, oid):
        locale = params.get_locale(req)

        r = self.context.db.tables.guideposts.data
        o = self.context.db.osmdata.node.data

        sql = sa.select(*NodeItem.make_selectables(r, o))\
                .where(r.c.id == oid)\
                .join(o, o.c.id == r.c.id)

        res = (await conn.execute(sql)).first()

        if res is None:
            raise falcon.HTTPNotFound()

        NodeItem('guidepost', oid).add_row_data(res, locale).to_response(resp)
