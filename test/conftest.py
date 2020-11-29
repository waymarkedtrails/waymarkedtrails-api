# SPDX-License-Identifier: GPL-3.0-only
#
# This file is part of the Waymarked Trails Map Project
# Copyright (C) 2020 Sarah Hoffmann

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

@pytest.fixture
def db():
    assert os.system('dropdb --if-exists ' + TEST_DATABASE) == 0
    assert os.system('createdb ' + TEST_DATABASE) == 0

    TestContext.init_globals('hiking')

    with TestContext.engine.begin() as conn:
        conn.execute("CREATE EXTENSION postgis")
        conn.execute(f"CREATE SCHEMA {TestContext.tables.site_config.DB_SCHEMA}")

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
def db_config(db):
    return TestContext.db_config
