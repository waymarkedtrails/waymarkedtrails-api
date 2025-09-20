# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of the Waymarked Trails Map Project
# Copyright (C) 2025 Sarah Hoffmann
import falcon
import pytest

pytestmark = [pytest.mark.parametrize("mapname", ['slopes'], indirect=True),
              pytest.mark.asyncio]


@pytest.fixture
def simple_way(conn, way_factory):
    return way_factory(458374, 'LINESTRING(0 0, 100 100)', name='Hello World',
                       intnames={'de': 'Hallo Welt', 'fr': 'Bonjour Monde'},
                       tags={'this': 'that', 'me': 'you'})


@pytest.fixture(params=[('de,en', 'Hallo Welt'),
                        ('ch', 'Hello World'),
                        ('es,fr', 'Bonjour Monde')])
def language_names(request):
    return request.param


async def test_info(wmt_call, simple_way, language_names):
    _, data = await wmt_call(f'/v1/details/way/{simple_way}',
                             headers={'Accept-Language': language_names[0]})

    assert data['type'] == 'way'
    assert data['id'] == simple_way
    assert data['name'] == language_names[1]

    route = data['route']
    assert route['route_type'] == 'route'
    assert isinstance(route['main'], list)
    assert len(route['main']) == 1
    main = route['main'][0]
    assert main['route_type'] == 'linear'
    assert isinstance(main['ways'], list)
    assert len(main['ways']) == 1
    way = main['ways'][0]
    assert way['route_type'] == 'base'
    assert way['tags'] == data['tags']
    assert way['id'] == data['id']


async def test_info_unknown(wmt_call, osm_ways_table, ways_table):
    status, _ = await wmt_call('/v1/details/way/11', expect_success=False)

    assert status == falcon.HTTP_NOT_FOUND


async def test_wikilink(wmt_call, conn, osm_ways_table):
    oid = 55
    conn.execute(osm_ways_table.data.insert()
                                    .values({'id': oid,
                                             'tags': {'wikipedia:de': 'Wolke',
                                                      'wikipedia:en': 'Cloud'},
                                             'nodes': [1, 2]}))

    status, data = await wmt_call(f'/v1/details/way/{oid}/wikilink',
                                  expect_success=False, as_json=False,
                                  headers={'Accept-Language': 'en,de'})

    assert status == falcon.HTTP_SEE_OTHER
    assert data == 'https://en.wikipedia.org/wiki/Cloud'

    status, data = await wmt_call(f'/v1/details/way/{oid}/wikilink',
                                  expect_success=False, as_json=False,
                                  headers={'Accept-Language': 'de,en'})

    assert status == falcon.HTTP_SEE_OTHER
    assert data == 'https://de.wikipedia.org/wiki/Wolke'


async def test_wikilink_unknown(wmt_call, osm_ways_table):
    status, _ = await wmt_call('/v1/details/way/11/wikilink', expect_success=False)

    assert status == falcon.HTTP_NOT_FOUND
