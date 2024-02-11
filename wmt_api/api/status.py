# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of the Waymarked Trails Map Project
# Copyright (C) 2023 Sarah Hoffmann

import sqlalchemy as sa

from ..common.json_writer import JsonWriter
from ..common.router import Router, needs_db

class APIStatus(Router):

    def add_routes(self, app, base):
        app.add_route(base, self)


    @needs_db
    async def on_get(self, conn, req, resp):
        status = self.context.db.status.table

        res = await conn.scalar(sa.select(status.c.date)
                                  .where(status.c.part == 'base'))

        out = JsonWriter().start_object()

        out.keyval('server_status', 'OK' if res else 'DOWN')
        out.keyval('last_update', res.isoformat() if res else '')

        out.end_object()

        out.to_response(resp)
