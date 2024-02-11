# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of the Waymarked Trails Map Project
# Copyright (C) 2024 Sarah Hoffmann
import asyncio

import pytest

pytestmark = [pytest.mark.parametrize("mapname", ["hiking"], indirect=True),
              pytest.mark.asyncio]


@pytest.fixture
def simple_segments(segment_factory):
    segment_factory('0 0, 10 10', 1)
    segment_factory('10 10, 50 50', 1, 2)
    segment_factory('50 50, 100 100', 1)
    segment_factory('2000 2000, 2100 2100', 3)
    segment_factory('0 0, -100 -100', 4)

@pytest.fixture
def simple_routes(simple_segments, route_factory, hierarchy_table):
    route_factory(1, 'LINESTRING(0 0, 100 100)')
    route_factory(2, 'LINESTRING(10 10, 50 50)')
    route_factory(3, 'LINESTRING(2000 2000, 2100 2100)')
    route_factory(4, 'LINESTRING(0 0, -100 -100)')


async def test_by_area(wmt_call, simple_routes):
    _, data = await wmt_call('/v1/list/by_area', params={'bbox': '1, 1, 50, 50'})

    assert len(data['results']) == 2

async def test_by_area_empty(wmt_call, simple_routes):
    _, data = await wmt_call('/v1/list/by_area', params={'bbox': '200, 200, 250, 250'})

    assert len(data['results']) == 0


async def test_byids(wmt_call, simple_routes):
    _, data = await wmt_call('/v1/list/by_ids', params={'relations': '3,4,5'})

    assert len(data['results']) == 2


async def test_byids_empty(wmt_call, simple_routes):
    _, data = await wmt_call('/v1/list/by_ids', params={'relations': '101'})

    assert len(data['results']) == 0


async def test_search(wmt_call, simple_segments, route_factory):
    route_factory(1, 'LINESTRING(0 0, 100 100)', name='Tree route')
    route_factory(2, 'LINESTRING(0 0, 100 100)', name='Foo',
                  intnames = {'de' : 'Tree route'})

    _, data = await wmt_call('/v1/list/search', params={'query': 'tree'})

    assert len(data['results']) == 1


async def test_segments(wmt_call, simple_routes):
    _, data = await wmt_call('/v1/list/segments',
                             params={'bbox': '50, 50, 1, 1', 'relations':'1,3'})

    assert len(data['features']) == 1

