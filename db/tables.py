# SPDX-License-Identifier: GPL-3.0-only
#
# This file is part of the Waymarked Trails Map Project
# Copyright (C) 2020 Sarah Hoffmann

import sqlalchemy as sa

def _status_table(meta):
    return sa.Table('status', meta,
                    sa.Column('part', sa.String, primary_key=True),
                    sa.Column('date', sa.DateTime(timezone=True)),
                    sa.Column('sequence', sa.Integer)
                   )

class RouteTables(object):
    """ Collection of table descriptions of a route database.
    """

    def __init__(self, schema : str):
        meta = sa.MetaData()

        self.status = _status_table(meta)

        meta = sa.MetaData(schema=schema)


