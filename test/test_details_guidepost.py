# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of the Waymarked Trails Map Project
# Copyright (C) 2024 Sarah Hoffmann
import asyncio

import falcon
import pytest

pytestmark = [pytest.mark.parametrize("mapname", ["hiking"], indirect=True),
              pytest.mark.asyncio]


async def test_info_simple(wmt_call, guidepost_factory):
    guidepost_factory(1, x=100, y=200, name='Foo', ele=34, tags={'name' : 'Foo'})

    _, data = await wmt_call(f'/v1/details/guidepost/1')

    assert data['type']  == 'guidepost'
    assert data['id'] == 1
    assert data['name'] == 'Foo'
    assert data['ele'] == 34
    assert data['x'] == 100
    assert data['y'] == 200


async def test_info_local_name_unused(wmt_call, guidepost_factory):
    guidepost_factory(1, x=100, y=200, name='Foo', ele=34,
                      tags={'name' : 'Foo', 'name:de' : 'Bar'})

    _, data = await wmt_call(f'/v1/details/guidepost/1',
                             headers={'Accept-Language': 'de,en'})

    assert data['name'] == 'Bar'
    assert data['local_name'] == 'Foo'


async def test_info_local_name_used(wmt_call, guidepost_factory):
    guidepost_factory(1, x=100, y=200, name='Foo', ele=34,
                      tags={'name' : 'Foo', 'name:de' : 'Bar'})

    _, data = await wmt_call(f'/v1/details/guidepost/1',
                             headers={'Accept-Language': 'en,fr'})

    assert data['name'] == 'Foo'
    assert 'local_name' not in data


async def test_info_bad_oid(wmt_call, guidepost_factory):
    guidepost_factory(1, x=100, y=200, name='Foo', ele=34, tags={'name' : 'Foo'})

    status, _ = await wmt_call(f'/v1/details/guidepost/2', expect_success=False)

    assert status == falcon.HTTP_NOT_FOUND
