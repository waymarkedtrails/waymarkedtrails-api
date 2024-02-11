# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of the Waymarked Trails Map Project
# Copyright (C) 2024 Sarah Hoffmann
import os
import importlib
import traceback

import falcon.asgi

from .common.context import Context
from .common.errors import APIError
from .api.status import APIStatus
from .api.symbols import APISymbols

async def print_traceback(req, resp, ex, params):
    traceback.print_exception(ex)

async def api_error_handler(req, resp, exception, _):
    """ Special error handler that passes message and content type as
        per exception info.
    """
    resp.status = exception.status
    resp.text = '{"error": "%s"}' % exception.msg
    resp.content_type = falcon.MEDIA_JSON


def create_app(context=None):
    if context is None:
        context = Context(os.environ.get('WMT_CONFIG', '') or 'hiking')

    app = falcon.asgi.App(cors_enable=True, media_type=falcon.MEDIA_JSON)
    app.add_error_handler(APIError, api_error_handler)
    if 'WMT_DEBUG' in os.environ:
        app.add_error_handler(Exception, print_traceback)
    APIStatus(context).add_routes(app, '/v1/status')
    APISymbols(context).add_routes(app, '/v1/symbols')

    map_type = importlib.import_module(f'wmt_api.api.{context.config.MAPTYPE}')

    map_type.APIListing(context).add_routes(app, '/v1/list')
    map_type.APITiles(context).add_routes(app, '/v1/tiles')
    map_type.APIDetails(context).add_routes(app, '/v1/details')

    return app


app = create_app()
