# SPDX-License-Identifier: GPL-3.0-only
#
# This file is part of the Waymarked Trails Map Project
# Copyright (C) 2020 Sarah Hoffmann

import xml.etree.ElementTree as ET

import pytest
import hug
import falcon
import shapely

import wmt_api.api.details.relation as api
import wmt_api.api.details.routes as routes_api

@pytest.fixture
def simple_route(conn, route_factory, hierarchy_table):
    oid = 458374

    route_factory(oid, 'LINESTRING(0 0, 100 100)', name='Hello World',
                  intnames={'de': 'Hallo Welt', 'fr' : 'Bonjour Monde'},
                  tags={'this' : 'that', 'me': 'you'},
                  members=[dict(id=1, type='W', role='')])

    return oid

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


def test_geometry_kml(route_geoms):
    response = hug.test.get(api, '/geometry/kml', oid=route_geoms)

    assert response.status == falcon.HTTP_OK

    root = ET.fromstring(response.data)
    assert root.tag == '{http://www.opengis.net/kml/2.2}kml'


def test_geometry_kml_locale_name(simple_route, language_names):
    response = hug.test.get(api, '/geometry/kml', oid=simple_route,
                            headers={'Accept-Language': language_names[0]})

    assert response.status == falcon.HTTP_OK

    root = ET.fromstring(response.data)
    ele = root.find('{http://www.opengis.net/kml/2.2}Document')
    assert ele
    assert ele.findtext('{http://www.opengis.net/kml/2.2}name') == language_names[1]


def test_geometry_kml_unknown(relations_table, route_table, hierarchy_table):
    assert hug.test.get(api, '/geometry/kml', oid=11).status == falcon.HTTP_NOT_FOUND


def test_geometry_gpx(route_geoms):
    response = hug.test.get(api, '/geometry/gpx', oid=route_geoms)

    assert response.status == falcon.HTTP_OK

    root = ET.fromstring(response.data)
    assert root.tag == '{http://www.topografix.com/GPX/1/1}gpx'


def test_geometry_gpx_locale_name(simple_route, language_names):
    response = hug.test.get(api, '/geometry/gpx', oid=simple_route,
                            headers={'Accept-Language': language_names[0]})

    assert response.status == falcon.HTTP_OK

    root = ET.fromstring(response.data)
    ele = root.find('{http://www.topografix.com/GPX/1/1}metadata')
    assert ele
    assert ele.findtext('{http://www.topografix.com/GPX/1/1}name') == language_names[1]


def test_geometry_gpx_unknown(relations_table, route_table, hierarchy_table):
    assert hug.test.get(api, '/geometry/gpx', oid=11).status == falcon.HTTP_NOT_FOUND
