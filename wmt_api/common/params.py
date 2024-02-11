# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of the Waymarked Trails Map Project
# Copyright (C) 2024 Sarah Hoffmann
"""
Functions for parameter conversion.
"""
from math import isnan

from ..common.errors import APIError
from ..common.types import Bbox


def as_str(req, name, default=None):
    value = req.params.get(name)

    if value is None:
        if default is None:
            raise APIError(f"Missing required parameter '{name}'")
        value = default

    return value[0] if isinstance(value, list) else value


def as_int(req, name, default=None, vmin=None, vmax=None):
    value = req.params.get(name)

    if value is None:
        if default is None:
            raise APIError(f"Missing required parameter '{name}'")
        else:
            value = default

    if isinstance(value, list):
        value = value[0]

    try:
        value = int(value)
    except ValueError:
        raise APIError(f"Parameter '{name}' must be a number.")

    if vmin is not None and value < vmin:
        value = vmin
    elif vmax is not None and value > vmax:
        value = vmax

    return value


def as_bbox(req, name):
    value = as_str(req, name)

    parts = value.split(',')
    if len(parts) != 4:
        raise APIError(f"Bounding box parameter '{name}' needs four values")

    try:
        coords = tuple([float(x) for x in parts])
    except ValueError:
        raise APIError(f"Bounding box parameter '{name}' has non-number values")

    if any(isnan(f) for f in coords):
        raise APIError(f"Bounding box parameter '{name}' has illegal values")

    return Bbox(*coords)


def as_int_list(req, name, default=None):
    values = as_str(req, name, default=default).split(',')
    try:
        return [int(v) for v in values if v]
    except ValueError:
        raise APIError(f"Parameter '{name}' must be a comma-separated list of numbers.")


def get_locale(req):
    header = req.get_header('accept-language', default='')
    if not header:
        return []

    langs = []
    pos = 0.0
    for lang in header.split(','):
        parts = lang.split(';q=')
        qual = float(parts[1]) if len(parts) > 1 else 1.0
        if qual <= 0.0:
            continue
        parts = parts[0].split('-')
        if len(parts) > 1:
            qual /= 2
        langs.append((qual - pos, parts[0]))
        pos += 0.000001

    langs.sort(reverse=True)
    seen = {}
    return [seen.setdefault(x, x) for _, x in langs if x not in seen]

