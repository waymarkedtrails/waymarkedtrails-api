# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of the Waymarked Trails Map Project
# Copyright (C) 2024 Sarah Hoffmann

from ..common.json_writer import JsonWriter
from .route_item import RouteItem

class RouteList:

    def __init__(self, **kwargs):
        self.items = 0
        self.to_ignore = 0
        self.out = JsonWriter()
        self.out.start_object()
        for k, v in kwargs.items():
            self.out.keyval(k, v)
        self.out.key('results').start_array()


    def __len__(self):
        return self.items


    def ignore_next_items(self, num):
        self.to_ignore = num


    def add_items(self, objs, locale, linear=None):
        for obj in objs:
            self.add_item(obj, locale, linear)


    def add_item(self, obj, locale, linear=None):
        if self.to_ignore > 0:
            self.to_ignore -= 1
        else:
            self.items += 1
            RouteItem(self.out, obj, locale, linear=linear).finish()
            self.out.next()


    def to_response(self, response):
        self.out.end_array().end_object()
        self.out.to_response(response)
