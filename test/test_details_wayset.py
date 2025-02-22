# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of the Waymarked Trails Map Project
# Copyright (C) 2024 Sarah Hoffmann
import asyncio

import falcon
import shapely
import xml.etree.ElementTree as ET
import pytest

pytestmark = [pytest.mark.parametrize("mapname", ['slopes'], indirect=True),
              pytest.mark.asyncio]

@pytest.fixture
def simple_way(conn, way_factory, joined_way_factory):
    way_factory(458374, 'LINESTRING(0 0, 100 100)', name='Hello World',
                       intnames={'de': 'Hallo Welt', 'fr' : 'Bonjour Monde'},
                       tags={'this' : 'that', 'me': 'you'})

    return joined_way_factory(458374)

@pytest.fixture(params=[('de,en', 'Hallo Welt'),
                       ('ch', 'Hello World'),
                       ('es,fr', 'Bonjour Monde')])
def language_names(request):
    return request.param


async def test_info(wmt_call, simple_way, language_names):
    _, data = await wmt_call(f'/v1/details/wayset/{simple_way}',
                             headers={'Accept-Language': language_names[0]})

    assert data['type'] == 'wayset'
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
    assert way['tags'] == {'this' : 'that', 'me': 'you'}
    assert way['id'] == 458374



async def test_info_unknown(wmt_call, osm_ways_table, ways_table, joined_ways_table):
    status, _ = await wmt_call('/v1/details/wayset/11', expect_success=False)

    assert status == falcon.HTTP_NOT_FOUND


async def test_wikilink(wmt_call, conn, osm_ways_table):
    oid = 55
    conn.execute(osm_ways_table.data.insert()\
        .values(dict(id=oid, tags={'wikipedia:de' : 'Wolke',
                                   'wikipedia:en' : 'Cloud'},
                     nodes=[1, 2])))

    status, data = await wmt_call(f'/v1/details/wayset/{oid}/wikilink',
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
    status, _ = await wmt_call('/v1/details/wayset/11/wikilink', expect_success=False)

    assert status == falcon.HTTP_NOT_FOUND


@pytest.fixture
def complex_way(conn, way_factory, joined_way_factory):
    way_factory(1, 'LINESTRING(0 0, 100 100)', tags={'this' : 'that', 'me': 'you'})
    way_factory(2, 'LINESTRING(100 100, 120 0)', tags={'this' : 'that', 'me': 'you'})
    way_factory(3, 'LINESTRING(100 100, 0 120)', tags={'this' : 'that', 'me': 'you'})
    way_factory(4, 'LINESTRING(0 120, 0 140)', tags={'this' : 'that', 'me': 'you'})

    return joined_way_factory(1, 2, 3, 4)


async def test_info_complex_way(wmt_call, complex_way):
    _, data = await wmt_call(f'/v1/details/wayset/{complex_way}')

    assert data['type'] == 'wayset'
    assert data['id'] == complex_way
    assert data['bbox'] == [0, 0, 120, 140]

    route = data['route']
    assert route['route_type'] == 'route'
    assert isinstance(route['main'], list)
    assert len(route['main']) == 1
    main = route['main'][0]
    assert main['route_type'] == 'linear'
    assert isinstance(main['ways'], list)
    assert len(main['ways']) == 4


async def test_geometry_geojson(wmt_call, complex_way):
    _, data = await wmt_call(f'/v1/details/wayset/{complex_way}/geometry/geojson')

    assert data['type'] == 'FeatureCollection'
    assert data['crs']['properties']['name'] == 'EPSG:3857'

    geom = shapely.geometry.shape(data['features'][0]['geometry'])


async def test_geometry_simplify(wmt_call, way_factory, joined_way_factory):
    oid1 = way_factory(84752, 'LINESTRING(0 0, 0.0001 0.1, 0 0.15)')
    oid2 = way_factory(5454, 'LINESTRING(0 0.15, 0 0.2)')

    oid = joined_way_factory(oid1, oid2)

    _, data = await wmt_call(f'/v1/details/wayset/{oid}/geometry/geojson')
    geom = shapely.geometry.shape(data['features'][0]['geometry'])
    assert geom.geom_type == 'LineString'
    assert len(geom.coords) == 4

    _, data = await wmt_call(f'/v1/details/wayset/{oid}/geometry/geojson',
                             params={'simplify': 2})
    geom = shapely.geometry.shape(data['features'][0]['geometry'])
    assert geom.geom_type == 'LineString'
    assert len(geom.coords) == 2


async def test_geometry_kml(wmt_call, complex_way):
    _, data = await wmt_call(f'/v1/details/wayset/{complex_way}/geometry/kml',
                             as_json=False)

    root = ET.fromstring(data)
    assert root.tag == '{http://www.opengis.net/kml/2.2}kml'


async def test_geometry_gpx(wmt_call, complex_way):
    _, data = await wmt_call(f'/v1/details/wayset/{complex_way}/geometry/gpx',
                             as_json=False)

    root = ET.fromstring(data)
    assert root.tag == '{http://www.topografix.com/GPX/1/1}gpx'


@pytest.mark.parametrize('geomtype', ['geojson', 'kml', 'gpx'])
async def test_geometry_unknown(wmt_call, ways_table, joined_ways_table, geomtype):
    status, _ = await wmt_call(f'/v1/details/wayset/11/geometry/{geomtype}',
                               expect_success=False)

    assert status == falcon.HTTP_NOT_FOUND


async def test_geometry_unknown_geometry_type(wmt_call, complex_way):
    status, data = await wmt_call(f'/v1/details/wayset/{complex_way}/geometry/fooson',
                                  expect_success=False)

    assert status == falcon.HTTP_BAD_REQUEST
    assert 'Supported geometry types' in data['error']
