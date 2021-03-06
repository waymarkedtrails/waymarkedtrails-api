# SPDX-License-Identifier: GPL-3.0-only
#
# This file is part of the Waymarked Trails Map Project
# Copyright (C) 2020 Sarah Hoffmann

from collections import OrderedDict

from .json_convert import JsonSerializable
from .route_item import RouteItem

class RouteList(JsonSerializable):

    def __init__(self, **kwargs):
        self.content = OrderedDict(**kwargs)
        self.content['results'] = []

    def set_items(self, res, locale):
        self.content['results'] = [RouteItem(r, locale) for r in res]

    def add_item(self, obj, locale):
        self.content['results'].append(RouteItem(obj, locale))

    def add_items(self, objs, locale):
        self.content['results'].extend([RouteItem(obj, locale) for obj in objs])

    def drop_leading_results(self, num):
        del self.content['results'][0:num]

    def __len__(self):
        return len(self.content['results'])

    def to_json_serializable(self):
        return self.content
