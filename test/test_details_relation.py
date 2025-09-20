# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of the Waymarked Trails Map Project
# Copyright (C) 2025 Sarah Hoffmann
import falcon
import pytest

pytestmark = [pytest.mark.parametrize("mapname", ['hiking', 'slopes'], indirect=True),
              pytest.mark.asyncio]


@pytest.fixture
def simple_route(conn, route_factory, hierarchy_table):
    return route_factory(458374, 'LINESTRING(0 0, 100 100)', name='Hello World',
                         intnames={'de': 'Hallo Welt', 'fr': 'Bonjour Monde'},
                         tags={'this': 'that', 'me': 'you'})


@pytest.fixture(params=[('de,en', 'Hallo Welt'),
                        ('ch', 'Hello World'),
                        ('es,fr', 'Bonjour Monde')])
def language_names(request):
    return request.param


@pytest.fixture(params=['LINESTRING(0 0, 100 100)',
                        'MULTILINESTRING((0 0, 100 100), (101 101, 200 200))'])
def route_geoms(request, conn, route_factory, hierarchy_table):
    return route_factory(84752, request.param)


async def test_info(wmt_call, simple_route, language_names):
    _, data = await wmt_call(f'/v1/details/relation/{simple_route}',
                             headers={'Accept-Language': language_names[0]})

    assert data['id'] == simple_route
    assert data['name'] == language_names[1]
    assert 'ref' not in data


async def test_info_with_superroute(wmt_call, conn, simple_route,
                                    route_factory, hierarchy_table,
                                    relations_table):
    route_factory(44, 'LINESTRING(0 0, 100 100)', name='Super')

    conn.execute(
        hierarchy_table.data.insert()
                            .values({'parent': 44, 'child': simple_route, 'depth': 2}))

    _, data = await wmt_call(f'/v1/details/relation/{simple_route}')

    assert 'superroutes' in data
    assert len(data['superroutes']) == 1

    rdata = data['superroutes']['44']

    assert rdata['id'] == 44
    assert rdata['name'] == 'Super'


async def test_info_unknown(wmt_call, relations_table, route_table, hierarchy_table):
    status, _ = await wmt_call('/v1/details/relation/11', expect_success=False)

    assert status == falcon.HTTP_NOT_FOUND


async def test_wikilink(wmt_call, conn, relations_table, route_table, hierarchy_table):
    oid = 55
    conn.execute(relations_table.data.insert()
                                     .values({'id': oid,
                                              'tags': {'wikipedia:de': 'Wolke',
                                                       'wikipedia:en': 'Cloud'},
                                              'members': [dict(id=1, type='W', role='')]}))

    status, data = await wmt_call(f'/v1/details/relation/{oid}/wikilink',
                                  expect_success=False, as_json=False,
                                  headers={'Accept-Language': 'en,de'})

    assert status == falcon.HTTP_SEE_OTHER
    assert data == 'https://en.wikipedia.org/wiki/Cloud'

    status, data = await wmt_call(f'/v1/details/relation/{oid}/wikilink',
                                  expect_success=False, as_json=False,
                                  headers={'Accept-Language': 'de,en'})

    assert status == falcon.HTTP_SEE_OTHER
    assert data == 'https://de.wikipedia.org/wiki/Wolke'


async def test_wikilink_unknown(wmt_call, simple_route):
    status, _ = await wmt_call('/v1/details/relation/11/wikilink', expect_success=False)

    assert status == falcon.HTTP_NOT_FOUND
