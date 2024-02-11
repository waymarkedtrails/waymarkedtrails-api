# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of the Waymarked Trails Map Project
# Copyright (C) 2023 Sarah Hoffmann


class APIError(Exception):
    """ A special exception class for errors raised during processing.
    """
    def __init__(self, msg, status=400):
        self.msg = msg
        self.status = status
