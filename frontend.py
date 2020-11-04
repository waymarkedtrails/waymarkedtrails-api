# SPDX-License-Identifier: GPL-3.0-only
#
# This file is part of the Waymarked Trails Map Project
# Copyright (C) 2020 Sarah Hoffmann

import hug
import os

hug.defaults.cli_output_format = hug.output_format.json

from wmt_api.api import base
from wmt_api.common.context import ApiContext

ApiContext.init_globals(os.environ['WMT_CONFIG'])

@hug.startup()
def init_settings(api):
    # see https://github.com/hugapi/hug/issues/623
    if hasattr(api.http, 'falcon'):
        api.http.falcon.req_options.auto_parse_qs_csv = False

@hug.context_factory()
def create_context(*args, **kwargs):
    return ApiContext()

hug.API(__name__).http.add_middleware(hug.middleware.CORSMiddleware(hug.API(__name__)))
hug.API(__name__).extend(base, '/api')

if ApiContext.db_config.MAPTYPE == 'routes':
    from wmt_api.api.listings import routes as listings
    from wmt_api.api.details import routes as details
    from wmt_api.api import tiles
    hug.API(__name__).extend(listings, '/api/list')
    hug.API(__name__).extend(details, '/api/details')
    hug.API(__name__).extend(tiles, '/api/tiles')
else:
    raise RuntimeError(f"No API specified for map type '{ApiContext.db_config.MAPTYPE}'")

application = __hug_wsgi__

if __name__ == '__main__':
    hug.API(__name__).cli()
