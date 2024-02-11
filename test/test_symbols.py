# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of the Waymarked Trails Map Project
# Copyright (C) 2024 Sarah Hoffmann
import asyncio

import pytest
import falcon

pytestmark = [pytest.mark.parametrize("mapname", ['hiking', 'slopes'], indirect=True),
              pytest.mark.asyncio]

@pytest.fixture
def symbol_dir(tmp_path, context):
    context.config.ROUTES.symbol_datadir = str(tmp_path)
    return tmp_path


async def test_unknown_id(wmt_call, db):
    status, _ = await wmt_call('/v1/symbols/id/4532222', expect_success=False)
    assert status == falcon.HTTP_NOT_FOUND


async def test_by_id(wmt_call, symbol_dir):
    sym_id = 'fg-435'
    svg = symbol_dir / f'{sym_id}.svg'
    svg.write_text('<svg></svg>')

    _, data = await wmt_call(f'/v1/symbols/id/{sym_id}', as_json=False)
    assert data == '<svg></svg>'


async def test_from_tags(wmt_call, symbol_dir):
    _, data = await wmt_call('/v1/symbols/from_tags/REG',
                             params={'ref': '23', 'piste:type': 'nordic',
                                     'color': 'red'},
                             as_json=False)
    assert '<svg' in data
    assert data.endswith('</svg>')


async def test_from_tags_unknown(wmt_call, symbol_dir):
    status, _ = await wmt_call('/v1/symbols/from_tags/REG',
                               params={'xx': 'foo'},
                               expect_success=False)
    assert status == falcon.HTTP_NOT_FOUND
