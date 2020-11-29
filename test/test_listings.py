# SPDX-License-Identifier: GPL-3.0-only
#
# This file is part of the Waymarked Trails Map Project
# Copyright (C) 2020 Sarah Hoffmann

import pytest
import hug
import falcon

import wmt_api.api.listings.routes as api


@pytest.fixture
def simple_segments(conn, segment_factory):
    segment_factory('0 0, 10 10', 1)
    segment_factory('10 10, 50 50', 1, 2)
    segment_factory('50 50, 100 100', 1)
    segment_factory('2000 2000, 2100 2100', 3)
    segment_factory('0 0, -100 -100', 4)

@pytest.fixture
def simple_routes(conn, simple_segments, route_factory, hierarchy_table):
    route_factory(1, 'LINESTRING(0 0, 100 100)')
    route_factory(2, 'LINESTRING(10 10, 50 50)')
    route_factory(3, 'LINESTRING(2000 2000, 2100 2100)')
    route_factory(4, 'LINESTRING(0 0, -100 -100)')

def test_by_area(simple_routes):
    response = hug.test.get(api, '/by_area', params={'bbox': '1, 1, 50, 50'})

    assert response.status == falcon.HTTP_OK
    assert len(response.data['results']) == 2

def test_by_area_empty(simple_routes):
    response = hug.test.get(api, '/by_area', params={'bbox': '200, 200, 250, 250'})

    assert response.status == falcon.HTTP_OK
    assert len(response.data['results']) == 0

def test_byids(simple_routes):
    response = hug.test.get(api, '/by_ids', params={'ids': '3,4,5'})

    assert response.status == falcon.HTTP_OK

def test_byids_empty(simple_routes):
    response = hug.test.get(api, '/by_ids', params={'ids': '101'})

    assert response.status == falcon.HTTP_OK
    assert len(response.data['results']) == 0

def test_search(simple_segments, route_factory):
    route_factory(1, 'LINESTRING(0 0, 100 100)', name='Tree route')
    route_factory(2, 'LINESTRING(0 0, 100 100)', name='Foo',
                  intnames = {'de' : 'Tree route'})

    response = hug.test.get(api, '/search', params={'query': 'tree'})

    assert response.status == falcon.HTTP_OK
    assert len(response.data['results']) == 1

def test_segments(simple_routes):
    response = hug.test.get(api, '/segments',
                            params={'bbox': '50, 50, 1, 1', 'relations':'1,3'})

    assert response.status == falcon.HTTP_OK
    assert len(response.data['features']) == 1
