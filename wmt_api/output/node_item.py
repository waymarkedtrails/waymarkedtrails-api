# SPDX-License-Identifier: GPL-3.0-only
#
# This file is part of the Waymarked Trails Map Project
# Copyright (C) 2024 Sarah Hoffmann

from osgende.common.tags import TagStore

from ..common.json_writer import JsonWriter

class NodeItem:
    """ Collects detailed information of route points like guideposts
        and network nodes.
    """

    @staticmethod
    def make_selectables(table, node_table):
        return [table.c.name, table.c.ele,
                table.c.geom.ST_X().label('x'), table.c.geom.ST_Y().label('y'),
                node_table.c.tags]

    def __init__(self, typ, oid):
        self.content = JsonWriter().start_object()\
                                   .keyval('type', typ)\
                                   .keyval('id', oid)

    def to_response(self, response):
        self.content.end_object().to_response(response)

    def add_row_data(self, row, locales):
        loctags = TagStore.make_localized(row.tags, locales)

        if 'name' in loctags:
            locname = loctags['name']
            self.content.keyval('name', locname)

            if row.name and row.name != locname:
                self.content.keyval('local_name', row.name)

        self.content.keyval_not_none('ele', row.ele)

        for tag in ('ref', 'operator', 'description', 'note'):
            self.content.keyval_not_none(tag, loctags.get(tag))

        self.content.keyval_not_none('image', loctags.get_url(keys=['image']))

        self.content.keyval('tags', row.tags)
        self.content.keyval('x', row.x)
        self.content.keyval('y', row.y)

        return self
