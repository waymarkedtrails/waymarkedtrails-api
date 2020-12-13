# SPDX-License-Identifier: GPL-3.0-only
#
# This file is part of the Waymarked Trails Map Project
# Copyright (C) 2020 Sarah Hoffmann

import pytest
import hug
import falcon

import wmt_api.api.tiles.routes as api

pytestmark = pytest.mark.parametrize("db", ["hiking"], indirect=True)

@pytest.fixture
def simple_segments(conn, segment_factory):
    segment_factory('0 0, 10 10', 1)
    segment_factory('10 10, 50 50', 1, 2)
    segment_factory('50 50, 100 100', 1)
    segment_factory('2000 2000, 2100 2100', 3)
    segment_factory('0 0, -100 -100', 4)

@pytest.fixture
def simple_routes(conn, style_factory, guidepost_table):
    style_factory('LINESTRING(0 0, 100 100)')
    style_factory('LINESTRING(10 10, 50 50)')
    style_factory('LINESTRING(2000 2000, 2100 2100)')
    style_factory('LINESTRING(0 0, -100 -100)')


def test_empty_tile(simple_routes):
    response = hug.test.get(api, '/12/0/0.json')

    assert response.status == falcon.HTTP_OK
    assert len(response.data['features']) == 0

def test_full_tile(simple_routes):
    response = hug.test.get(api, '/12/2048/2047.json')

    assert response.status == falcon.HTTP_OK
    assert len(response.data['features']) == 4
