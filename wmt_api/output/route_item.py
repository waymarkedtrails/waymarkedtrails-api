# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of the Waymarked Trails Map Project
# Copyright (C) 2024 Sarah Hoffmann

import sqlalchemy as sa
from geoalchemy2 import Geography
from geoalchemy2.shape import to_shape
from osgende.common.tags import TagStore
from wmt_db.common.route_types import Network

from wmt_db.common.route_types import Network

def _get_network(row):
    mapping = row._mapping
    network = mapping.get('network', None)
    if network is not None:
        return network

    level = mapping.get('level', None)
    if level is not None:
        return Network.from_int(level).name

    return mapping.get('piste', None)


class RouteItem:

    _columns = ('id', 'name', 'intnames', 'symbol', 'level', 'ref',
                'piste', 'network', 'itinerary', 'linear')

    @classmethod
    def make_selectables(cls, table):
        return [ table.c[col] for col in cls._columns if col in table.c]

    def __init__(self, writer, row, locales=[], objtype='relation'):
        self.out = writer
        self.out.start_object()
        self._add_row_data(row, locales, objtype)


    def _add_row_data(self, row, locales, objtype):
        self.out.keyval('type', row._mapping.get('type', objtype))

        for e in ('id', 'ref'):
            self._add_optional(e, row, e)

        for l in locales:
            if l in row.intnames:
                self.out.keyval('name', row.intnames[l])
                if row.intnames[l] != row.name:
                    self.out.keyval('local_name', row.name)
                break
        else:
            self._add_optional('name', row, 'name')

        self.out.keyval('group', _get_network(row))
        self.out.keyval('linear', row.linear)
        self._add_optional('symbol_description', row, None,
                           row.intnames.get('symbol'))

        self._add_optional('itinerary', row, 'itinerary')
        self._add_optional('symbol_id', row, 'symbol')


    def _add_optional(self, name, row, key, default=None):
        value = row._mapping.get(key, None)
        if value is None:
            value = default
        if value is not None:
            self.out.keyval(name, value)


    def finish(self):
        self.out.end_object()


class DetailedRouteItem(RouteItem):

    @classmethod
    def make_selectables(cls, table):
        fields = [ table.c[col] for col in cls._columns if col in table.c]
        if 'level' not in table.c and 'piste' in table.c:
            fields.append(table.c.piste)

        fields.append(table.c.route)
        fields.append(table.c.geom.ST_Envelope().label('bbox'))
        fields.append(table.c.tags)

        return fields

    def __init__(self, writer, row, locales=[], objtype='relation'):
        super().__init__(writer, row, locales, objtype)
        self._add_details(row, locales)

    def _add_details(self, row, locales):
        loctags = TagStore.make_localized(row.tags, locales)

        self.out.keyval('linear', row.linear)
        self._add_optional('official_length', row, None,
                           loctags.get_length('distance', 'length', unit='m'))

        for tag in ('operator', 'note', 'description'):
            self._add_optional(tag, row, None, loctags.get(tag))

        self._add_optional('url', row, None, loctags.get_url())
        self._add_optional('wikipedia', row, None, loctags.get_wikipedia_tags() or None)

        self.out.keyval('bbox', to_shape(row.bbox).bounds)
        self.out.keyval('tags', row.tags)

        self.out.key('route').raw(row.route).next()


    def add_extra_route_info(self, key, routes, locales=[]):
        self.out.key(key).start_object()

        for route in routes:
            self.out.key(str(route.id))
            RouteItem(self.out, route, locales).finish()
            self.out.next()

        self.out.end_object().next()
