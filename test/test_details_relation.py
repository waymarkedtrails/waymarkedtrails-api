# SPDX-License-Identifier: GPL-3.0-only
#
# This file is part of the Waymarked Trails Map Project
# Copyright (C) 2022 Sarah Hoffmann

import xml.etree.ElementTree as ET

import pytest
import hug
import falcon
import shapely

import wmt_api.api.details.relation as api
import wmt_api.api.details.routes as routes_api

pytestmark = pytest.mark.parametrize("db", ["hiking", "slopes"], indirect=True)

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


def test_info(simple_route, language_names):
    response = hug.test.get(api, '/', oid=simple_route,
                            headers={'Accept-Language': language_names[0]})
    assert response.status == falcon.HTTP_OK
    data = response.data
    assert data['id'] == simple_route
    assert data['name'] == language_names[1]
    assert 'ref' not in data


def test_info_via_routes(simple_route, language_names):
    response = hug.test.get(routes_api, f'/relation/{simple_route}',
                            headers={'Accept-Language': language_names[0]})
    assert response.status == falcon.HTTP_OK
    data = response.data
    assert data['id'] == simple_route
    assert data['name'] == language_names[1]


def test_info_unknown(relations_table, route_table, hierarchy_table):
    assert hug.test.get(api, '/', oid=11).status == falcon.HTTP_NOT_FOUND


def test_wikilink(conn, relations_table, route_table, hierarchy_table):
    oid = 55
    conn.execute(relations_table.data.insert()\
        .values(dict(id=oid, tags={'wikipedia:de' : 'Wolke',
                                   'wikipedia:en' : 'Cloud'},
                     members=[dict(id=1, type='W', role='')])))

    response = hug.test.get(api, '/wikilink', oid=oid,
                            headers={'Accept-Language': 'en,de'})
    assert response.status == falcon.HTTP_TEMPORARY_REDIRECT
    assert response.headers_dict['location']\
             == 'https://en.wikipedia.org/wiki/Cloud'

    response = hug.test.get(api, '/wikilink', oid=oid,
                            headers={'Accept-Language': 'de,en'})
    assert response.status == falcon.HTTP_TEMPORARY_REDIRECT
    assert response.headers_dict['location']\
             == 'https://de.wikipedia.org/wiki/Wolke'


def test_wikilink_unknown(simple_route):
    assert hug.test.get(api, '/wikilink', oid=11).status == falcon.HTTP_NOT_FOUND


@pytest.fixture(params=['LINESTRING(0 0, 100 100)',
                        'MULTILINESTRING((0 0, 100 100), (101 101, 200 200))'])
def route_geoms(request, conn, route_factory, hierarchy_table):
    return route_factory(84752, request.param)

def test_geometry_geojson(route_geoms):
    response = hug.test.get(api, '/geometry/geojson', oid=route_geoms)

    assert response.status == falcon.HTTP_OK

    assert response.data['type'] == 'FeatureCollection'
    assert response.data['crs']['properties']['name'] == 'EPSG:3857'

    geom = shapely.geometry.shape(response.data['features'][0]['geometry'])


def test_geometry_geojson_unknown(relations_table, route_table, hierarchy_table):
    assert hug.test.get(api, '/geometry/geojson', oid=11).status == falcon.HTTP_NOT_FOUND


class GoemetryParamsGPX:
    endpoint = '/geometry/gpx'
    root_tag = '{http://www.topografix.com/GPX/1/1}gpx'

    @staticmethod
    def get_name(response):
        root = ET.fromstring(response.data)
        ele = root.find('{http://www.topografix.com/GPX/1/1}metadata')
        assert ele
        return ele.findtext('{http://www.topografix.com/GPX/1/1}name')


class GoemetryParamKML:
    endpoint = '/geometry/kml'
    root_tag = '{http://www.opengis.net/kml/2.2}kml'

    @staticmethod
    def get_name(response):
        root = ET.fromstring(response.data)
        ele = root.find('{http://www.opengis.net/kml/2.2}Document')
        assert ele
        return ele.findtext('{http://www.opengis.net/kml/2.2}name')


@pytest.mark.parametrize('params', (GoemetryParamsGPX, GoemetryParamKML))
class TestOtherGeometries:
    @staticmethod
    def test_geometry_other(route_geoms, params):
        response = hug.test.get(api, params.endpoint, oid=route_geoms)

        assert response.status == falcon.HTTP_OK

        root = ET.fromstring(response.data)
        assert root.tag == params.root_tag


    @staticmethod
    def test_geometry_other_unknown(relations_table, route_table, hierarchy_table, params):
        assert hug.test.get(api, params.endpoint, oid=11).status == falcon.HTTP_NOT_FOUND


    @staticmethod
    def test_geometry_kml_locale_name(simple_route, language_names, params):
        response = hug.test.get(api, params.endpoint, oid=simple_route,
                                headers={'Accept-Language': language_names[0]})

        assert response.status == falcon.HTTP_OK
        assert params.get_name(response) == language_names[1]


    @staticmethod
    def test_geometry_ref_name(conn, route_factory, hierarchy_table, params):
        oid = route_factory(458374, 'LINESTRING(0 0, 100 100)',
                            ref='34', tags={'this' : 'that', 'me': 'you'})

        response = hug.test.get(api, params.endpoint, oid=oid)

        assert response.status == falcon.HTTP_OK
        assert params.get_name(response) == '34'



    @staticmethod
    def test_geometry_no_name(conn, route_factory, hierarchy_table, params):
        oid = route_factory(458374, 'LINESTRING(0 0, 100 100)',
                            tags={'this' : 'that', 'me': 'you'})

        response = hug.test.get(api, params.endpoint, oid=oid)

        assert response.status == falcon.HTTP_OK
        assert params.get_name(response) == str(oid)
