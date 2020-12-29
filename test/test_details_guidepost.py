# SPDX-License-Identifier: GPL-3.0-only
#
# This file is part of the Waymarked Trails Map Project
# Copyright (C) 2020 Sarah Hoffmann

import pytest
import hug
import falcon

import wmt_api.api.details.guidepost as api

from compares import HugGetJson

@pytest.mark.parametrize("db", ["hiking"], indirect=True)
def test_info_simple(guidepost_factory):
    guidepost_factory(1, x=100, y=200, name='Foo', ele=34, tags={'name' : 'Foo'})

    response = HugGetJson(api, '/', oid=1)

    assert dict(type='guidepost', id=1, name='Foo', ele=34, x=100, y=200) in response

@pytest.mark.parametrize("db", ["hiking"], indirect=True)
def test_info_local_name_unused(guidepost_factory):
    guidepost_factory(1, x=100, y=200, name='Foo', ele=34,
                      tags={'name' : 'Foo', 'name:de' : 'Bar'})

    response = HugGetJson(api, '/', oid=1, headers={'Accept-Language': 'de,en'})

    assert dict(name='Bar', local_name='Foo') in response

@pytest.mark.parametrize("db", ["hiking"], indirect=True)
def test_info_local_name_used(guidepost_factory):
    guidepost_factory(1, x=100, y=200, name='Foo', ele=34,
                      tags={'name' : 'Foo', 'name:de' : 'Bar'})

    response = HugGetJson(api, '/', oid=1, headers={'Accept-Language': 'en,fr'})

    assert dict(name='Foo') in response
    assert 'local_name' not in response


@pytest.mark.parametrize("db", ["hiking"], indirect=True)
def test_info_bad_oid(guidepost_factory):
    guidepost_factory(1, x=100, y=200, name='Foo', ele=34, tags={'name' : 'Foo'})

    assert HugGetJson(api, '/', oid=2).status() == falcon.HTTP_NOT_FOUND
