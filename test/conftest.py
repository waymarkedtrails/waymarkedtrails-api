# SPDX-License-Identifier: GPL-3.0-only
#
# This file is part of the Waymarked Trails Map Project
# Copyright (C) 2020 Sarah Hoffmann

import itertools
import os

import pytest
import hug
from sqlalchemy import create_engine
from sqlalchemy.engine.url import URL

from wmt_api.common.context import ApiContext

TEST_DATABASE = 'test_wmt_api'

class TestContext(ApiContext):

    @classmethod
    def create_engine(cls):
        cls.engine = create_engine(URL('postgresql', database=TEST_DATABASE),
                                   echo=False)

def create_context(*args, **kwargs):
    return TestContext()

hug.defaults.context_factory = create_context

@pytest.fixture(params=('hiking', 'slopes'))
def db(request):
    assert os.system('dropdb --if-exists ' + TEST_DATABASE) == 0
    assert os.system('createdb ' + TEST_DATABASE) == 0

    TestContext.init_globals(request.param)

    with TestContext.engine.begin() as conn:
        conn.execute("CREATE EXTENSION postgis")
        conn.execute(f"CREATE SCHEMA {TestContext.tables.site_config.DB_SCHEMA}")
        conn.execute('CREATE EXTENSION pg_trgm')

    yield TestContext.engine

    if hasattr(TestContext.thread_data, 'conn'):
        TestContext.thread_data.conn.close()
    TestContext.engine.dispose()

@pytest.fixture
def conn(db):
    with db.connect().execution_options(autocommit=True) as conn:
        yield conn

@pytest.fixture
def status_table(conn):
    TestContext.tables.status.create(conn)
    return TestContext.tables.status

@pytest.fixture
def relations_table(conn):
    TestContext.tables.osmdata.relation.create(conn)
    return TestContext.tables.osmdata.relation

@pytest.fixture
def hierarchy_table(conn):
    TestContext.tables.tables.hierarchy.create(conn)
    return TestContext.tables.tables.hierarchy

@pytest.fixture
def route_table(conn):
    TestContext.tables.tables.routes.data.create(conn)
    return TestContext.tables.tables.routes

@pytest.fixture
def route_factory(conn, relations_table, route_table):
    def factory(oid, geom, **kwargs):
        conn.execute(relations_table.data.insert()
            .values(dict(id=oid, tags=kwargs.get('tags', {}),
                         members=kwargs.get('members', [dict(id=1, type='W', role='')]))))

        values = dict(intnames={}, country='de', network='', level=0, top=True)
        values.update(kwargs)
        values['id'] = oid
        values['geom'] = f'SRID=3857;{geom}'
        values = { k: v for k, v in values.items() if k in route_table.data.c }
        conn.execute(route_table.data.insert().values(values))
        return oid

    return factory

@pytest.fixture
def segments_table(conn):
    TestContext.tables.tables.segments.data.create(conn)
    return TestContext.tables.tables.segments

@pytest.fixture
def segment_factory(conn, segments_table):
    segment_id = itertools.count(1)
    def factory(geom, *rels, nodes={}, ways={}):
        conn.execute(segments_table.data.insert()
                      .values(dict(id=next(segment_id), nodes=nodes,
                                   ways=ways, rels=rels,
                                   geom=f'SRID=3857;LINESTRING({geom})')))

    return factory

@pytest.fixture
def db_config(db):
    return TestContext.db_config
