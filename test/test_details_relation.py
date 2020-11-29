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

@pytest.fixture
def simple_route(conn, relations_table, route_table, hierarchy_table):
    oid = 458374

    conn.execute(relations_table.data.insert()\
        .values(dict(id=oid, tags={'this' : 'that', 'me': 'you'},
                     members=[dict(id=1, type='W', role='')])))

    conn.execute(route_table.data.insert()\
        .values(dict(id=oid, name='Hello World', symbol='test', country='de',
                     level=0, top=True, intnames={},
                     geom='SRID=3857;LINESTRING(0 0, 100 100)')))

    return oid


def test_info(simple_route):
    response = hug.test.get(api, '/', oid=simple_route)
    assert response.status == falcon.HTTP_OK
    data = response.data
    assert data['id'] == simple_route
    assert data['name'] == 'Hello World'


def test_info_unknown(simple_route):
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


@pytest.fixture(params=['SRID=3857;LINESTRING(0 0, 100 100)',
                        'SRID=3857;MULTILINESTRING((0 0, 100 100), (101 101, 200 200))'])
def route_geoms(request, conn, relations_table, route_table, hierarchy_table):
    oid = 85736

    conn.execute(relations_table.data.insert()\
        .values(dict(id=oid, tags={}, members=[dict(id=1, type='W', role='')])))

    conn.execute(route_table.data.insert()\
        .values(dict(id=oid, symbol='test', country='de',
                     level=0, top=True, intnames={},
                     geom=request.param)))

    return oid

def test_geometry_geojson(route_geoms):
    response = hug.test.get(api, '/geometry/geojson', oid=route_geoms)

    assert response.status == falcon.HTTP_OK

    assert response.data['type'] == 'FeatureCollection'
    assert response.data['crs']['properties']['name'] == 'EPSG:3857'

    geom = shapely.geometry.shape(response.data['features'][0]['geometry'])

def test_geometry_kml(route_geoms):
    response = hug.test.get(api, '/geometry/kml', oid=route_geoms)

    assert response.status == falcon.HTTP_OK

    root = ET.fromstring(response.data)
    assert root.tag == '{http://www.opengis.net/kml/2.2}kml'


def test_geometry_gpx(route_geoms):
    response = hug.test.get(api, '/geometry/gpx', oid=route_geoms)

    assert response.status == falcon.HTTP_OK

    root = ET.fromstring(response.data)
    assert root.tag == '{http://www.topografix.com/GPX/1/1}gpx'