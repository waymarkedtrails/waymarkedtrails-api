# SPDX-License-Identifier: GPL-3.0-only
#
# This file is part of the Waymarked Trails Map Project
# Copyright (C) 2020 Sarah Hoffmann

from collections import OrderedDict

from .json_convert import JsonSerializable
from wmt_db.common.route_types import Network


class RouteItem(JsonSerializable):

    _columns = ('id', 'name', 'intnames', 'symbol', 'level', 'ref',
                              'network', 'itinerary')

    @classmethod
    def make_selectables(cls, table):
        return [ table.c[col] for col in cls._columns if col in table.c]

    def __init__(self, row, locales=[]):
        self.content = OrderedDict()
        self._set_row_data(row, locales)

    def set_items(self, res):
        self.content['results'] = [RouteItem(r) for r in res]

    def to_json_serializable(self):
        return self.content

    def _set_row_data(self, row, locales):
        self._add_optional('type', row, 'type', 'relation')

        for e in ('id', 'ref'):
            self._add_optional(e, row, e)

        for l in locales:
            if l in row['intnames']:
                self.content['name'] = row['intnames'][l]
                if self.content['name'] != row['name']:
                    self.content['local_name'] = row['name']
                break
        else:
            self._add_optional('name', row, 'name')

        self.content['group'] = self._get_network(row)
        self._add_optional('symbol_description', row, None,
                           row['intnames'].get('symbol'))

        self._add_optional('itinerary', row, 'itinerary')
        self._add_optional('symbol_id', row, 'symbol')

    def _add_optional(self, name, row, key, default=None):
        if key is not None and key in row and row[key]:
            self.content[name] = row[key]
        elif default is not None:
            self.content[name] = default

    def _get_network(self, row):
        if 'network' in row and row['network'] is not None:
            return row['network']

        return Network.from_int(row['level']).name

