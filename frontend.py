# SPDX-License-Identifier: GPL-3.0-only
#
# This file is part of the Waymarked Trails Map Project
# Copyright (C) 2020 Sarah Hoffmann

from wmt_api import api
from wmt_api.common.context import ApiContext
import hug
import os

@hug.startup()
def init_settings(api):
    # see https://github.com/hugapi/hug/issues/623
    if hasattr(api.http, 'falcon'):
        api.http.falcon.req_options.auto_parse_qs_csv = False

    ApiContext.init_globals(os.environ['WMT_CONFIG'])


@hug.context_factory()
def create_context(*args, **kwargs):
    return ApiContext()

hug.API(__name__).extend(api, '/api')

application = __hug_wsgi__

if __name__ == '__main__':
    hug.API(__name__).cli()
