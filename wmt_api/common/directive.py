# SPDX-License-Identifier: GPL-3.0-only
#
# This file is part of the Waymarked Trails Map Project
# Copyright (C) 2020 Sarah Hoffmann

import hug

from .context import ApiContext

def parse_language_header(header):
    if not header:
        return []

    langs = []
    for lang in header.split(','):
        parts = lang.split(';q=')
        qual = float(parts[1]) if len(parts) > 1 else 1.0
        if qual <= 0.0:
            continue
        parts = parts[0].split('-')
        if len(parts) > 1:
            qual /= 2
        langs.append((qual, parts[0]))

    sorted(langs)
    seen = {}
    return [seen.setdefault(x, x) for _, x in langs if x not in seen]



@hug.directive()
def locale(default=False, interface=None, request=None, argparse=None, **kwargs):
    if isinstance(interface, hug.interface.CLI):
        _, unknown = argparse.parse_known_args()
        try:
            pos = unknown.index('--locale')
            if pos + 1 < len(unknown):
                return unknown[pos + 1].split(',')
        except ValueError:
            pass
    elif isinstance(interface, hug.interface.HTTP):
        return parse_language_header(request.get_header('ACCEPT-LANGUAGE'))

    return []

@hug.directive()
def connection(default=False, context : ApiContext=None, **kwargs):
    return context.connection

@hug.directive()
def status_table(default=False, context : ApiContext=None, **kwargs):
    return context.tables.status

@hug.directive()
def tables(default=False, context : ApiContext=None, **kwargs):
    return context.tables.tables

@hug.directive()
def osmdata(default=False, context : ApiContext=None, **kwargs):
    return context.tables.osmdata

@hug.directive()
def shield_factory(default=False, context : ApiContext=None, **kwargs):
    return context.shield_config

@hug.directive()
def db_config(default=False, context : ApiContext=None, **kwargs):
    return context.db_config

@hug.directive()
def api_config(default=False, context : ApiContext=None, **kwargs):
    return context.api_config
