# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of the Waymarked Trails Map Project
# Copyright (C) 2024 Sarah Hoffmann
import asyncio
import os
import itertools

import pytest
import falcon
from falcon import testing
import sqlalchemy as sa

from wmt_api.frontend import create_app
from wmt_api.common.context import Context

TEST_DATABASE = 'test_wmt_api'


@pytest.fixture()
def mapname(request):
    return request.param


@pytest.fixture()
def context(mapname, event_loop):
    url = sa.engine.url.URL.create('postgresql+psycopg', database=TEST_DATABASE)
    context = Context(mapname, url=url)

    yield context

    event_loop.run_until_complete(context.engine.dispose())


@pytest.fixture
def wmt_call(context):
    app = create_app(context)
    async def _get(url, params=None, expect_success=True, as_json=True,
                   headers={}):
        async with testing.ASGIConductor(app) as conductor:
            response = await conductor.simulate_get(url, params=params, headers=headers)
            if expect_success:
                assert response.status == falcon.HTTP_OK,\
                       f"Unexpected status: {response.status}\nText: {response.text}"
            if as_json:
                assert response.json is not None,\
                       f"Response is not valid json: {response.text}"

            if response.status_code >=300 and response.status_code < 400:
                out_text = response.headers['location']
            elif as_json:
                out_text = response.json
            else:
                out_text = response.text

            return response.status, out_text

    yield _get


@pytest.fixture
def db(mapname, context):
    assert os.system('dropdb --if-exists ' + TEST_DATABASE) == 0
    assert os.system('createdb ' + TEST_DATABASE) == 0

    url = sa.engine.url.URL.create('postgresql', database=TEST_DATABASE)
    engine = sa.create_engine(url)

    with engine.begin() as conn:
        conn.execute(sa.text('CREATE EXTENSION postgis'))
        conn.execute(sa.text(f"CREATE SCHEMA {context.db.site_config.DB_SCHEMA}"))
        conn.execute(sa.text('CREATE EXTENSION pg_trgm'))

    yield engine

    engine.dispose()


@pytest.fixture
def conn(db):
    with db.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        yield conn


@pytest.fixture
def status_table(db, context):
    context.db.status.create(db)
    return context.db.status


@pytest.fixture
def hierarchy_table(db, context):
    context.db.tables.hierarchy.create(db)
    return context.db.tables.hierarchy


@pytest.fixture
def segments_table(db, context):
    context.db.tables.segments.data.create(db)
    return context.db.tables.segments


@pytest.fixture
def relations_table(db, context):
    context.db.osmdata.relation.create(db)
    return context.db.osmdata.relation


@pytest.fixture
def route_table(db, context):
    context.db.tables.routes.data.create(db)
    return context.db.tables.routes


@pytest.fixture
def osm_ways_table(db, context):
    context.db.osmdata.way.create(db)
    return context.db.osmdata.way


@pytest.fixture
def osm_nodes_table(db, context):
    context.db.osmdata.node.create(db)
    return context.db.osmdata.node


@pytest.fixture
def ways_table(db, context):
    if 'ways' in context.db.tables:
        context.db.tables.ways.data.create(db)
        return context.db.tables.ways


@pytest.fixture
def joined_ways_table(db, context):
    if 'joined_ways' in context.db.tables:
        context.db.tables.joined_ways.data.create(db)
        return context.db.tables.joined_ways


@pytest.fixture
def style_table(db, context):
    context.db.tables.style.data.create(db)
    return context.db.tables.style


@pytest.fixture
def guidepost_table(db, context):
    context.db.tables.guideposts.data.create(db)
    return context.db.tables.guideposts


@pytest.fixture
def style_factory(conn, style_table):
    segment_id = itertools.count(1)
    def factory(geom, *kwargs):
        geom=f'SRID=3857;{geom}'
        conn.execute(style_table.data.insert()
                       .values(dict(id=next(segment_id), geom=geom,
                                    geom100=geom, *kwargs)))

    return factory


@pytest.fixture
def way_factory(conn, osm_ways_table, ways_table):
    def factory(oid, geom, **kwargs):
        conn.execute(osm_ways_table.data.insert()
            .values(dict(id=oid, tags=kwargs.get('tags', {}),
                         nodes=kwargs.get('nodes', [1, 2, 3, 4]))))

        values = dict(intnames={}, network='', top=True)
        values.update(kwargs)
        values['id'] = oid
        values['geom'] = f'SRID=3857;{geom}'
        values = { k: v for k, v in values.items() if k in ways_table.data.c }
        conn.execute(ways_table.data.insert().values(values))
        return oid

    return None if ways_table is None else factory


@pytest.fixture
def joined_way_factory(conn, joined_ways_table):
    def factory(*ids):
        conn.execute(joined_ways_table.data.insert()
                       .values([dict(id=ids[0], child=x) for x in ids]))
        return ids[0]

    return None if joined_ways_table is None else factory


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
def segment_factory(conn, segments_table):
    segment_id = itertools.count(1)
    def factory(geom, *rels, nodes={}, ways={}):
        conn.execute(segments_table.data.insert()
                      .values(dict(id=next(segment_id), nodes=nodes,
                                   ways=ways, rels=rels,
                                   geom=f'SRID=3857;LINESTRING({geom})')))

    return factory


@pytest.fixture
def guidepost_factory(conn, guidepost_table, osm_nodes_table):
    def factory(oid, x, y, name=None, ele=None, tags=None):
        conn.execute(guidepost_table.data.insert()
                       .values(dict(id=oid, name=name, ele=ele,
                                    geom=f'SRID=3857;POINT({x} {y})')))
        conn.execute(osm_nodes_table.data.insert()
                       .values(dict(id=oid, tags=tags or {}, geom='SRID=4326;POINT(0 0)')))

    return factory

