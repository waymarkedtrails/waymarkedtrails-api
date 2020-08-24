# SPDX-License-Identifier: GPL-3.0-only
#
# This file is part of the Waymarked Trails Map Project
# Copyright (C) 2020 Sarah Hoffmann

import hug
from math import isnan
import collections

class Bbox(collections.UserList):
    """A bounding box geometry.
    """

    def __init__(self, value):
        if isinstance(value, tuple):
            coords = value
        else:
            parts = value.split(',')
            coords = tuple([float(x) for x in parts])

        if len(coords) != 4:
            raise ValueError("Bbox argument expects for numbers.")
        if any(isnan(f) for f in coords):
            raise ValueError("Bbox argument has invalid coordinates.")

        super().__init__(coords)

    def as_sql(self):
        return func.ST_SetSrid(func.ST_MakeBox2D(
                    WKTElement('POINT(%f %f)' % self.data[0:2]),
                    WKTElement('POINT(%f %f)' % self.data[2:4])), 3857)

    def center_as_sql(self):
        return func.ST_SetSrid(WKTElement('POINT(%f %f)' %
                                ((self.coords[2] + self.data[0])/2,
                                 (self.coords[1] + self.data[3])/2)), 3857)


@hug.type(extend=hug.types.text)
def bbox_type(value):
    "A bounding box of the form: `x1,y2,x2,y2`."
    return Bbox(value)

