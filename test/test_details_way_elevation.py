# SPDX-License-Identifier: GPL-3.0-only
#
# This file is part of the Waymarked Trails Map Project
# Copyright (C) 2025 Sarah Hoffmann
import asyncio

import pytest
import falcon

pytestmark = [pytest.mark.asyncio]


@pytest.fixture
def simple_route(conn, route_factory, hierarchy_table, relway_factory):
    relway_factory(119489294,
                'LINESTRING(1069126.08187597 5962419.305238,1069131.87048949 5962405.88946843,1069140.25284715 5962400.24503497,1069156.30511772 5962398.11814795,1069169.05119941 5962394.32247395,1069172.90285379 5962390.33047376,1069179.61541909 5962381.8720204,1069185.07007414 5962374.23160635,1069191.86056308 5962366.47667475)',
                rels=[3972279])
    relway_factory(35939583,
                'LINESTRING(1069191.86056308 5962366.47667475,1069209.28206339 5962365.28235045,1069224.55509752 5962366.44395353,1069256.43699969 5962370.32141845,1069283.61008739 5962364.69336867,1069305.8628536 5962367.31106579)',
                rels=[3972279])
    relway_factory(298793003,
                'LINESTRING(1069327.62581405 5962368.14545691,1069337.85607525 5962365.87133228,1069347.60766265 5962359.21256787,1069356.98076377 5962341.33045672,1069359.06243825 5962320.65073264,1069355.4445548 5962294.08128586,1069350.81366398 5962274.33421877,1069351.69308796 5962267.26651385,1069360.05318172 5962261.21316003,1069377.64166126 5962250.25169221,1069401.17460162 5962225.9892685, 1069415.12293381 5962218.54531525,1069423.90604164 5962215.5513754,1069437.60947095 5962215.37141184,1069447.9176558 5962214.43887343,1069458.64885471 5962215.37141184,1069468.31138651 5962216.74567915,1069479.69937042 5962222.8644434,1069491.74413932 5962233.72771457,1069510.835432 5962274.18697486,1069524.96187538 5962305.61542613,1069531.74123237 5962314.7609468,1069543.69694568 5962318.29481783)',
                rels=[3972279])
    return route_factory(3972279, 'LINESTRING(1069126.08187597 5962419.305238,1069131.87048949 5962405.88946843)',
                         tags={"ref": "147", "name": "Guschg - Steg",
                               "type": "route", "route": "hiking",
                               "source": "llv.li", "network": "lwn",
                               "distance": "8.53 km",
                               "osmc:symbol": "red:red:white_bar:147:black"},
                         members=[{"id": 119489294, "role": "", "type": "W"},
                                  {"id": 35939583, "role": "", "type": "W"},
                                  {"id": 298793003, "role": "", "type": "W"},
                                  {"id": 298792994, "role": "", "type": "W"}],
                         name='Guschg - Steg', ref='147',
                         symbol='osmc_LOC_red_bar_white_003100340037_black',
                         country='li', level=3, top=True, intnames={}, network='')

def check_elevation_response(data):
    minele = data['min_elevation']
    maxele = data['max_elevation']

    assert minele > 1000
    assert maxele < 2000
    assert minele < maxele

    assert data['segments']

    for k, segment in data['segments'].items():
        assert k.isdigit()
        assert segment['elevation']
        for pt in segment['elevation']:
            assert 'x' in pt
            assert 'y' in pt
            assert pt['ele'] <= maxele
            assert pt['ele'] >= minele
            assert isinstance(pt['pos'], (int, float))


@pytest.mark.parametrize("mapname", ["hiking"], indirect=True)
async def test_relation_elevation(wmt_call, simple_route):
    check_elevation_response(
        (await wmt_call(f'/v1/details/relation/{simple_route}/way-elevation'))[1])
