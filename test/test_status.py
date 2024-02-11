# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of the Waymarked Trails Map Project
# Copyright (C) 2024 Sarah Hoffmann
import asyncio

import pytest
from datetime import datetime, timezone

pytestmark = [pytest.mark.parametrize("mapname", ['hiking', 'slopes'], indirect=True),
              pytest.mark.asyncio]

async def test_status_missing_date(wmt_call, status_table):
    _, data = await wmt_call('/v1/status')
    assert data['server_status'] == 'DOWN'


async def test_status_ok(wmt_call, conn, status_table):
    test_date = datetime.now(timezone.utc)
    status_table.set_status(conn, 'base', test_date, 123)

    _, data = await wmt_call('/v1/status')
    assert data['server_status'] == 'OK'
    assert datetime.fromisoformat(data['last_update']) == test_date
