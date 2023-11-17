# SPDX-License-Identifier: GPL-3.0-only
#
# This file is part of the Waymarked Trails Map Project
# Copyright (C) 2020-2023 Sarah Hoffmann

from collections import OrderedDict
from sqlalchemy import func
from geoalchemy2.shape import to_shape

from osgende.common.tags import TagStore
from wmt_db.common.route_types import Network

from .json_convert import JsonSerializable


class RouteItem(JsonSerializable):

    _columns = ('id', 'name', 'intnames', 'symbol', 'level', 'ref',
                'piste', 'network', 'itinerary')

    @classmethod
    def make_selectables(cls, table):
        return [ table.c[col] for col in cls._columns if col in table.c]

    def __init__(self, row, locales=[], objtype='relation'):
        self.content = OrderedDict()
        self._set_row_data(row, locales, objtype)

    def to_json_serializable(self):
        return self.content

    def _set_row_data(self, row, locales, objtype):
        self.content['type'] = row._mapping.get('type', objtype)

        for e in ('id', 'ref'):
            self._add_optional(e, row, e)

        for l in locales:
            if l in row.intnames:
                self.content['name'] = row.intnames[l]
                if self.content['name'] != row.name:
                    self.content['local_name'] = row.name
                break
        else:
            self._add_optional('name', row, 'name')

        self.content['group'] = self._get_network(row)
        self._add_optional('symbol_description', row, None,
                           row.intnames.get('symbol'))

        self._add_optional('itinerary', row, 'itinerary')
        self._add_optional('symbol_id', row, 'symbol')

    def _add_optional(self, name, row, key, default=None):
        value = row._mapping.get(key, None)
        if value is None:
            value = default
        if value is not None:
            self.content[name] = value if value is not None else default

    def _get_network(self, row):
        mapping = row._mapping
        network = mapping.get('network', None)
        if network is not None:
            return network

        level = mapping.get('level', None)
        if level is not None:
            return Network.from_int(level).name

        return mapping.get('piste', None)


class DetailedRouteItem(RouteItem):

    @classmethod
    def make_selectables(cls, table, rel_table):
        fields = [ table.c[col] for col in cls._columns if col in table.c]
        if 'level' not in table.c and 'piste' in table.c:
            fields.append(table.c.piste)

        fields.append(func.ST_Length2dSpheroid(func.ST_Transform(table.c.geom, 4326),
                           'SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]]').label("length"))
        fields.append(table.c.geom.ST_Envelope().label('bbox'))
        fields.append(rel_table.c.tags)

        return fields

    def __init__(self, row, locales=[], objtype='relation'):
        super().__init__(row, locales, objtype)
        self._add_details(row, locales)

    def _add_details(self, row, locales):
        loctags = TagStore.make_localized(row.tags, locales)

        self.content['mapped_length'] = int(row.length)
        self._add_optional('official_length', row, None,
                           loctags.get_length('distance', 'length', unit='m'))

        for tag in ('operator', 'note', 'description'):
            self._add_optional(tag, row, None, loctags.get(tag))

        self._add_optional('url', row, None, loctags.get_url())
        self._add_optional('wikipedia', row, None, loctags.get_wikipedia_tags() or None)

        self.content['bbox'] = to_shape(row.bbox).bounds
        self.content['tags'] = row.tags

    def add_extra_info(self, key, value):
        self.content[key] = value
