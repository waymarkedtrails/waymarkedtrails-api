# SPDX-License-Identifier: GPL-3.0-only
#
# This file is part of the Waymarked Trails Map Project
# Copyright (C) 2020 Sarah Hoffmann

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from geoalchemy2 import Geometry

def _status_table(meta):
    return sa.Table('status', meta,
                    sa.Column('part', sa.String, primary_key=True),
                    sa.Column('date', sa.DateTime(timezone=True)),
                    sa.Column('sequence', sa.Integer)
                   )

def _routes_table(meta):
        table = sa.Table('routes', meta,
                        sa.Column('id', sa.BigInteger,
                                  primary_key=True, autoincrement=False),
                        sa.Column('name', sa.String),
                        sa.Column('intnames', JSONB),
                        sa.Column('ref', sa.String),
                        sa.Column('itinerary', JSONB),
                        sa.Column('symbol', sa.String),
                        sa.Column('country', sa.String(length=3)),
                        sa.Column('network', sa.String(length=3)),
                        sa.Column('level', sa.SmallInteger),
                        sa.Column('top', sa.Boolean),
                        sa.Column('geom', Geometry('GEOMETRY', srid=3857)))


class RouteTables(object):
    """ Collection of table descriptions of a route database.
    """

    def __init__(self, schema : str):
        meta = sa.MetaData()

        self.status = _status_table(meta)

        meta = sa.MetaData(schema=schema)

        self.routes = _routes_table(meta)
