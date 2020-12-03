# SPDX-License-Identifier: GPL-3.0-only
#
# This file is part of the Waymarked Trails Map Project
# Copyright (C) 2020 Sarah Hoffmann

import pytest
import hug
import falcon

from wmt_api.api import symbols

pytestmark = pytest.mark.parametrize("db", ["hiking", "slopes"], indirect=True)

@pytest.fixture
def symbol_dir(tmp_path, db_config):
    db_config.ROUTES.symbol_datadir = str(tmp_path)
    return tmp_path

def test_unknown_id(db):
    response = hug.test.get(symbols, '/id/4532222')
    assert response.status == falcon.HTTP_NOT_FOUND

def test_by_id(symbol_dir):
    sym_id = 'fg-435'
    svg = symbol_dir / f'{sym_id}.svg'
    svg.write_text('<svg></svg>')

    response = hug.test.get(symbols, f'/id/{sym_id}')
    assert response.status == falcon.HTTP_OK
    assert response.data == '<svg></svg>'

def test_from_tags(symbol_dir):
    response = hug.test.get(symbols, 'from_tags/REG',
                            {'ref': '23', 'piste:type': 'nordic', 'color': 'red'})
    assert response.status == falcon.HTTP_OK

def test_from_tags_unknown(symbol_dir):
    response = hug.test.get(symbols, 'from_tags/REG', {'xx': 'foo'})
    assert response.status == falcon.HTTP_NOT_FOUND

