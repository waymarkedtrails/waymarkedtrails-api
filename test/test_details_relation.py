# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of the Waymarked Trails Map Project
# Copyright (C) 2024 Sarah Hoffmann
import asyncio

import falcon
import shapely
import xml.etree.ElementTree as ET
import pytest

pytestmark = [pytest.mark.parametrize("mapname", ['hiking', 'slopes'], indirect=True),
              pytest.mark.asyncio]

@pytest.fixture
def simple_route(conn, route_factory, hierarchy_table):
    return route_factory(458374, 'LINESTRING(0 0, 100 100)', name='Hello World',
                         intnames={'de': 'Hallo Welt', 'fr' : 'Bonjour Monde'},
                         tags={'this' : 'that', 'me': 'you'})


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


@pytest.mark.parametrize('htype', ['superroutes', 'subroutes'])
async def test_info_with_superroute(wmt_call, conn, simple_route,
                                    route_factory, hierarchy_table,
                                    relations_table, htype):
    route_factory(44, 'LINESTRING(0 0, 100 100)', name='Super')

    if htype == 'superroutes':
        conn.execute(hierarchy_table.data.insert()
                       .values({'parent': 44, 'child': simple_route, 'depth': 2}))
    else:
        r = relations_table.data
        conn.execute(r.delete().where(r.c.id == simple_route))
        conn.execute(r.insert()
                       .values({'id': simple_route, 'tags': {'type': 'route'}, 'members': [{'id': 44, 'role': '', 'type': 'R'}]}))

    _, data = await wmt_call(f'/v1/details/relation/{simple_route}')

    assert htype in data
    assert len(data[htype]) == 1

    rdata = data[htype][0]

    assert rdata['id'] == 44
    assert rdata['name'] == 'Super'



async def test_info_unknown(wmt_call, relations_table, route_table, hierarchy_table):
    status, _ = await wmt_call('/v1/details/relation/11', expect_success=False)

    assert status == falcon.HTTP_NOT_FOUND


async def test_wikilink(wmt_call, conn, relations_table, route_table, hierarchy_table):
    oid = 55
    conn.execute(relations_table.data.insert()\
        .values(dict(id=oid, tags={'wikipedia:de' : 'Wolke',
                                   'wikipedia:en' : 'Cloud'},
                     members=[dict(id=1, type='W', role='')])))

    status, data = await wmt_call(f'/v1/details/relation/{oid}/wikilink',
                                  expect_success=False, as_json=False,
                                  headers={'Accept-Language': 'en,de'})

    assert status == falcon.HTTP_SEE_OTHER
    assert data  == 'https://en.wikipedia.org/wiki/Cloud'

    status, data = await wmt_call(f'/v1/details/relation/{oid}/wikilink',
                                  expect_success=False, as_json=False,
                                  headers={'Accept-Language': 'de,en'})

    assert status == falcon.HTTP_SEE_OTHER
    assert data == 'https://de.wikipedia.org/wiki/Wolke'


async def test_wikilink_unknown(wmt_call, simple_route):
    status, _ = await wmt_call('/v1/details/relation/11/wikilink', expect_success=False)

    assert status == falcon.HTTP_NOT_FOUND


async def test_geometry_geojson(wmt_call, route_geoms):
    _, data = await wmt_call(f'/v1/details/relation/{route_geoms}/geometry/geojson')

    assert data['type'] == 'FeatureCollection'
    assert data['crs']['properties']['name'] == 'EPSG:3857'

    geom = shapely.geometry.shape(data['features'][0]['geometry'])
    assert geom.geom_type in ('LineString', 'MultiLineString')
    assert geom.length > 0


async def test_geometry_simplify(wmt_call, route_factory):
    oid = route_factory(84752, 'LINESTRING(0 0, 0.0001 0.1, 0 0.15)')

    _, data = await wmt_call(f'/v1/details/relation/{oid}/geometry/geojson')
    geom = shapely.geometry.shape(data['features'][0]['geometry'])
    assert geom.geom_type == 'LineString'
    assert len(geom.coords) == 3

    _, data = await wmt_call(f'/v1/details/relation/{oid}/geometry/geojson',
                             params={'simplify': 2})
    geom = shapely.geometry.shape(data['features'][0]['geometry'])
    assert geom.geom_type == 'LineString'
    assert len(geom.coords) == 2


async def test_geometry_geojson_unknown(wmt_call, relations_table, route_table, hierarchy_table):
    status, _ = await wmt_call('/v1/details/relation/11/geometry/geojson',
                               expect_success=False)

    assert status == falcon.HTTP_NOT_FOUND


async def test_geometry_unknown_geometry(wmt_call, simple_route):
    status, data = await wmt_call(f'/v1/details/relation/{simple_route}/geometry/fooson',
                                  expect_success=False)

    assert status == falcon.HTTP_BAD_REQUEST
    assert 'Supported geometry types' in data['error']


class GoemetryParamsGPX:
    endpoint = 'geometry/gpx'
    root_tag = '{http://www.topografix.com/GPX/1/1}gpx'

    @staticmethod
    def get_name(data):
        root = ET.fromstring(data)
        ele = root.find('{http://www.topografix.com/GPX/1/1}metadata')
        assert ele
        return ele.findtext('{http://www.topografix.com/GPX/1/1}name')


class GoemetryParamKML:
    endpoint = 'geometry/kml'
    root_tag = '{http://www.opengis.net/kml/2.2}kml'

    @staticmethod
    def get_name(data):
        root = ET.fromstring(data)
        ele = root.find('{http://www.opengis.net/kml/2.2}Document')
        assert ele
        return ele.findtext('{http://www.opengis.net/kml/2.2}name')


@pytest.mark.parametrize('params', (GoemetryParamsGPX, GoemetryParamKML))
class TestOtherGeometries:
    @staticmethod
    async def test_geometry_other(wmt_call, route_geoms, params):
        _, data = await wmt_call(f'/v1/details/relation/{route_geoms}/{params.endpoint}',
                                 as_json=False)

        root = ET.fromstring(data)
        assert root.tag == params.root_tag


    @staticmethod
    async def test_geometry_other_unknown(wmt_call, relations_table, route_table,
                                          hierarchy_table, params):
        status, _ = await wmt_call(f'/v1/details/relation/11/{params.endpoint}',
                                   expect_success=False)

        assert status == falcon.HTTP_NOT_FOUND


    @staticmethod
    async def test_geometry_locale_name(wmt_call, simple_route, language_names, params):
        _, data = await wmt_call(f'/v1/details/relation/{simple_route}/{params.endpoint}',
                                 as_json=False,
                                 headers={'Accept-Language': language_names[0]})

        assert params.get_name(data) == language_names[1]


    @staticmethod
    async def test_geometry_ref_name(wmt_call, conn, route_factory, hierarchy_table, params):
        oid = route_factory(458374, 'LINESTRING(0 0, 100 100)',
                            ref='34', tags={'this' : 'that', 'me': 'you'})

        _, data = await wmt_call(f'/v1/details/relation/{oid}/{params.endpoint}',
                                 as_json=False)

        assert params.get_name(data) == '34'



    @staticmethod
    async def test_geometry_no_name(wmt_call, conn, route_factory, hierarchy_table, params):
        oid = route_factory(458374, 'LINESTRING(0 0, 100 100)',
                            tags={'this' : 'that', 'me': 'you'})

        _, data = await wmt_call(f'/v1/details/relation/{oid}/{params.endpoint}',
                                 as_json=False)

        assert params.get_name(data) == str(oid)
