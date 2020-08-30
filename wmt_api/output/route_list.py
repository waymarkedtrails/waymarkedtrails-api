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

    def set_items(self, res):
        self.content['results'] = [RouteItem(r) for r in res]

    def to_json_serializable(self):
        if 'results' not in self.content:
            self.set_items([])
        return self.content
