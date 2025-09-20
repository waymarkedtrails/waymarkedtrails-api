# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of the Waymarked Trails Map Project
# Copyright (C) 2025 Sarah Hoffmann

import pytest
import shapely

pytestmark = [pytest.mark.parametrize("mapname", ["slopes"], indirect=True),
              pytest.mark.asyncio]


@pytest.fixture
def simple_routes(conn, style_factory, way_factory, joined_ways_table):
    style_factory('LINESTRING(0 0, 100 100)')
    style_factory('LINESTRING(10 10, 50 50)')
    style_factory('LINESTRING(2000 2000, 2100 2100)')
    style_factory('LINESTRING(0 0, -100 -100)')
    way_factory(1001, 'LINESTRING(0 0, -100 -100)')


async def test_empty_tile(wmt_call, simple_routes):
    _, data = await wmt_call('/v1/tiles/12/0/0.json')

    assert len(data['features']) == 0


async def test_full_tile(wmt_call, simple_routes):
    _, data = await wmt_call('/v1/tiles/12/2048/2047.json')

    assert len(data['features']) == 3

    for feat in data['features']:
        print(feat)
        assert 'properties' in feat
        geom = shapely.geometry.shape(feat['geometry'])
        assert geom.geom_type == 'LineString'
