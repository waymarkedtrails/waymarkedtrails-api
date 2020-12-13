# SPDX-License-Identifier: GPL-3.0-only
#
# This file is part of the Waymarked Trails Map Project
# Copyright (C) 2020 Sarah Hoffmann

import pytest
import hug
import falcon

import wmt_api.api.listings.slopes as slopes_api

pytestmark = pytest.mark.parametrize("db", ["slopes"], indirect=True)

@pytest.fixture
def api(mapname):
    return slopes_api

@pytest.fixture
def simple_segments(conn, segment_factory):
    segment_factory('0 0, 10 10', 1)
    segment_factory('10 10, 50 50', 1, 2)
    segment_factory('50 50, 100 100', 1)
    segment_factory('2000 2000, 2100 2100', 3)
    segment_factory('0 0, -100 -100', 4)

@pytest.fixture
def simple_routes(conn, simple_segments, route_factory, hierarchy_table,
                  way_factory, joined_way_factory):
    route_factory(1, 'LINESTRING(0 0, 100 100)')
    route_factory(2, 'LINESTRING(10 10, 50 50)')
    route_factory(3, 'LINESTRING(2000 2000, 2100 2100)')
    route_factory(4, 'LINESTRING(0 0, -100 -100)')

    way_factory(100, 'LINESTRING(25 25, 25 50)', name='Foo')
    way_factory(101, 'LINESTRING(0 25, 25 25)', name='Foo')
    way_factory(102, 'LINESTRING(50 50, 50 0)', name='Bar')

    joined_way_factory(100, 101)

def test_by_area(simple_routes, api):
    response = hug.test.get(api, '/by_area', params={'bbox': '1, 1, 50, 50'})

    assert response.status == falcon.HTTP_OK
    assert len(response.data['results']) == 4

def test_by_area_empty(simple_routes, api):
    response = hug.test.get(api, '/by_area', params={'bbox': '200, 200, 250, 250'})

    assert response.status == falcon.HTTP_OK
    assert len(response.data['results']) == 0

def test_byids(simple_routes, api):
    response = hug.test.get(api, '/by_ids', params={'relations': '3,4,5',
                                                    'ways': '100, 101',
                                                    'waysets': '100'})

    assert response.status == falcon.HTTP_OK
    assert len(response.data['results']) == 5

def test_byids_empty(simple_routes, api):
    response = hug.test.get(api, '/by_ids', params={'ids': '101'})

    assert response.status == falcon.HTTP_OK
    assert len(response.data['results']) == 0

def test_search_route(simple_routes, route_factory, api):
    route_factory(11, 'LINESTRING(0 0, 100 100)', name='Tree route')
    route_factory(12, 'LINESTRING(0 0, 100 100)', name='Foo',
                  intnames = {'de' : 'Tree route'})

    response = hug.test.get(api, '/search', params={'query': 'tree'})

    assert response.status == falcon.HTTP_OK
    assert len(response.data['results']) == 1

def test_search_way(simple_routes, way_factory, joined_way_factory, api):
    way_factory(300, 'LINESTRING(25 25, 25 50)', name='Wubble way')
    way_factory(301, 'LINESTRING(0 25, 25 25)', name='Wubble way')
    way_factory(302, 'LINESTRING(50 50, 50 0)', name='Wubble way')

    joined_way_factory(300, 301)

    response = hug.test.get(api, '/search', params={'query': 'wubble'})

    assert response.status == falcon.HTTP_OK
    assert len(response.data['results']) == 2

def test_segments(simple_routes, api):
    response = hug.test.get(api, '/segments',
                            params={'bbox': '50, 50, 1, 1', 'relations':'1,3',
                                    'ways': '100,102', 'waysets': '100'})

    assert response.status == falcon.HTTP_OK
    assert len(response.data['features']) == 4
