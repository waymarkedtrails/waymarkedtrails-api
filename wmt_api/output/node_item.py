# SPDX-License-Identifier: GPL-3.0-only
#
# This file is part of the Waymarked Trails Map Project
# Copyright (C) 2020 Sarah Hoffmann

from collections import OrderedDict

from osgende.common.tags import TagStore

from .json_convert import JsonSerializable

class NodeItem(JsonSerializable):
    """ Collects detailed information of route points like guideposts
        and network nodes.
    """

    @staticmethod
    def make_selectables(table, node_table):
        return [table.c.name, table.c.ele,
                table.c.geom.ST_X().label('x'), table.c.geom.ST_Y().label('y'),
                node_table.c.tags]

    def __init__(self, typ, oid):
        self.content = OrderedDict(type=typ, id=oid)

    def to_json_serializable(self):
        return self.content

    def add_if(self, key, value):
        if value is not None:
            self.content[key]  = value

    def add_row_data(self, row, locales):
        loctags = TagStore.make_localized(row['tags'], locales)

        if 'name' in loctags:
            self.content['name'] = loctags['name']

            if row['name'] and row['name'] != self.content['name']:
                self.content['local_name'] = row['name']

        self.add_if('ele', row['ele'])

        for tag in ('ref', 'operator', 'description', 'note'):
            self.add_if(tag, loctags.get(tag))

        self.add_if('image', loctags.get_url(keys=['image']))

        for key in ('tags', 'x', 'y'):
            self.content[key] = row[key]

        return self
