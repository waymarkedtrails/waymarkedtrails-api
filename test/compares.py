# SPDX-License-Identifier: GPL-3.0-only
#
# This file is part of the Waymarked Trails Map Project
# Copyright (C) 2020 Sarah Hoffmann
"""
More complex assertion functions.
"""

import hug
import falcon

class HugGetJson:

    def __init__(self, *args, **kwargs):
        self.response = hug.test.get(*args, **kwargs)
        self.explain_assert = []

    def _add_msg(self, line):
        self.explain_assert.append(line)

    def _new_msg(self, line):
        self.explain_assert = [line + ':']
        if self.response.status != falcon.HTTP_OK:
            self._add_msg(f'Bad status: {self.response.status}')
            return False

        self._add_msg(f'Full response: {self.response.data}')
        return True

    def __contains__(self, item):
        if isinstance(item, str):
            return self.contains_key(item)

        return self.contains_dict(item)

    def contains_key(self, item):
        if not self._new_msg(f'Json response contains key {item}'):
            return False

        if item not in self.response.data:
            self._add_msg(f'Missing key: {item}')
            return False

        return True

    def contains_dict(self, item):
        if not self._new_msg(f'Json response contains data {item}'):
            return False

        data = self.response.data
        for key, value in item.items():
            if key not in data:
                self._add_msg(f'Missing key: {key}')
                return False
            if data[key] != value:
                self._add_msg(f'Bad data for "{key}". Expected: {value}, got: {data[key]}')
                return False

        return True

    def status(self):
        return self.response.status
