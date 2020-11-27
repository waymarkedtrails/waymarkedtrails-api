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
        print("create_engine CALLED")
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

    yield TestContext.engine

    if hasattr(TestContext.thread_data, 'conn'):
        TestContext.thread_data.conn.close()
    TestContext.engine.dispose()


@pytest.fixture
def status_table(db):
    with db.begin() as conn:
        TestContext.tables.status.create(conn)

    return TestContext.tables.status

@pytest.fixture
def db_config(db):
    return TestContext.db_config
