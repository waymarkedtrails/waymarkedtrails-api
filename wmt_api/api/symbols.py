# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of the Waymarked Trails Map Project
# Copyright (C) 2020-2023 Sarah Hoffmann
from pathlib import Path

import aiofiles
import falcon

from ..common.router import Router


class APISymbols(Router):

    def add_routes(self, app, base):
        app.add_route(base + '/from_tags/{style}', self, suffix='from_tags')
        app.add_route(base + '/id/{symbol}', self, suffix='by_uuid')


    async def on_get_from_tags(self, req, resp, style):
        """ Create a route shield from a set of OSM tags. The tag list must be
            given as keyword parameters."""
        sym = self.context.shield_factory.create(req.params, '', style=style)
        if sym is None:
            raise falcon.HTTPNotFound()

        resp.text = sym.create_image('svg')
        resp.content_type = 'image/svg+xml'


    async def on_get_by_uuid(self, req, resp, symbol):
        """ Retrive a symbol SVG by its ID. These are the IDs returned by the API
            for the routes."""
        if not '.' in symbol:
            symbol += '.svg'
        filename = Path(self.context.config.ROUTES.symbol_datadir) / symbol

        if not filename.exists():
            raise falcon.HTTPNotFound()

        async with aiofiles.open(filename, 'rb') as output:
            resp.data = await output.read()

        resp.content_type = 'image/svg+xml'
