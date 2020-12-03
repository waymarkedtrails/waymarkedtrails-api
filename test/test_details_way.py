# SPDX-License-Identifier: GPL-3.0-only
#
# This file is part of the Waymarked Trails Map Project
# Copyright (C) 2020 Sarah Hoffmann

import xml.etree.ElementTree as ET

import pytest
import hug
import falcon
import shapely

import wmt_api.api.details.way as api
import wmt_api.api.details.slopes as slopes_api

pytestmark = pytest.mark.parametrize("db", ["slopes"], indirect=True)

@pytest.fixture
def simple_way(conn, way_factory):
    return way_factory(458374, 'LINESTRING(0 0, 100 100)', name='Hello World',
                       intnames={'de': 'Hallo Welt', 'fr' : 'Bonjour Monde'},
                       tags={'this' : 'that', 'me': 'you'})

@pytest.fixture(params=[('de,en', 'Hallo Welt'),
                       ('ch', 'Hello World'),
                       ('es,fr', 'Bonjour Monde')])
def language_names(request):
    return request.param


def test_info(simple_way, language_names):
    response = hug.test.get(api, '/', oid=simple_way,
                            headers={'Accept-Language': language_names[0]})
    assert response.status == falcon.HTTP_OK
    data = response.data
    assert data['id'] == simple_way
    assert data['name'] == language_names[1]


def test_info_via_routes(simple_way):
    response = hug.test.get(slopes_api, f'/way/{simple_way}')
    assert response.status == falcon.HTTP_OK
    data = response.data
    assert data['id'] == simple_way
    assert data['name'] == 'Hello World'


def test_info_unknown(conn, osm_ways_table, ways_table):
    assert hug.test.get(api, '/', oid=11).status == falcon.HTTP_NOT_FOUND


def test_wikilink(conn, osm_ways_table):
    oid = 55
    conn.execute(osm_ways_table.data.insert()\
        .values(dict(id=oid, tags={'wikipedia:de' : 'Wolke',
                                   'wikipedia:en' : 'Cloud'},
                     nodes=[1, 2])))

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


def test_wikilink_unknown(osm_ways_table):
    assert hug.test.get(api, '/wikilink', oid=11).status == falcon.HTTP_NOT_FOUND


def test_geometry_geojson(simple_way):
    response = hug.test.get(api, '/geometry/geojson', oid=simple_way)

    assert response.status == falcon.HTTP_OK

    assert response.data['type'] == 'FeatureCollection'
    assert response.data['crs']['properties']['name'] == 'EPSG:3857'

    geom = shapely.geometry.shape(response.data['features'][0]['geometry'])


def test_geometry_geojson_unknown(osm_ways_table, ways_table):
    assert hug.test.get(api, '/geometry/geojson', oid=11).status == falcon.HTTP_NOT_FOUND


def test_geometry_kml(simple_way):
    response = hug.test.get(api, '/geometry/kml', oid=simple_way)

    assert response.status == falcon.HTTP_OK

    root = ET.fromstring(response.data)
    assert root.tag == '{http://www.opengis.net/kml/2.2}kml'


def test_geometry_kml_unknown(osm_ways_table, ways_table):
    assert hug.test.get(api, '/geometry/kml', oid=11).status == falcon.HTTP_NOT_FOUND


def test_geometry_gpx(simple_way):
    response = hug.test.get(api, '/geometry/gpx', oid=simple_way)

    assert response.status == falcon.HTTP_OK

    root = ET.fromstring(response.data)
    assert root.tag == '{http://www.topografix.com/GPX/1/1}gpx'


def test_geometry_gpx_unknown(osm_ways_table, ways_table):
    assert hug.test.get(api, '/geometry/gpx', oid=11).status == falcon.HTTP_NOT_FOUND
