# SPDX-License-Identifier: GPL-3.0-only
#
# This file is part of the Waymarked Trails Map Project
# Copyright (C) 2020 Sarah Hoffmann

import hug
import falcon
import json
from datetime import datetime, timezone

from wmt_api.api import base

def test_status_missing_date(db, status_table):
    response = hug.test.get(base, 'v1/status')
    assert response.status == falcon.HTTP_OK
    assert response.data['server_status'] == 'DOWN'

def test_status_ok(db, status_table):
    test_date = datetime.now(timezone.utc)
    with db.begin() as conn:
        status_table.set_status(conn, 'base', test_date, 123)

    response = hug.test.get(base, 'v1/status')
    assert response.status == falcon.HTTP_OK
    assert response.data['server_status'] == 'OK'
    assert datetime.fromisoformat(response.data['last_update']) == test_date
