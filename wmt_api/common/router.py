# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of the Waymarked Trails Map Project
# Copyright (C) 2023 Sarah Hoffmann

def needs_db(func):
    async def _impl(self, *method_args, **method_kwargs):
        async with self.context.engine.begin() as conn:
            await func(self, conn, *method_args, **method_kwargs)

    return _impl

class Router:

    def __init__(self, context):
        self.context = context
