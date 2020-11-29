# SPDX-License-Identifier: GPL-3.0-only
#
# This file is part of the Waymarked Trails Map Project
# Copyright (C) 2020 Sarah Hoffmann

from math import isnan
import collections

import hug
from sqlalchemy import func
from geoalchemy2.elements import WKTElement

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
                    WKTElement(f'POINT({self[0]} {self[1]})'),
                    WKTElement(f'POINT({self[2]} {self[3]})')), 3857)

    def center_as_sql(self):
        return func.ST_SetSrid(WKTElement('POINT({} {})'.format(
                                (self.coords[2] + self.data[0])/2.0,
                                (self.coords[1] + self.data[3])/2.0)), 3857)


@hug.type(extend=hug.types.text)
def bbox_type(value):
    "A bounding box of the form: `x1,y2,x2,y2`."
    return Bbox(value)


class ListOfIds(hug.types.DelimitedList):
    """A list of route ids.."""

    def __call__(self, value):
        value = super().__call__(value)
        return [int(number) for number in value]

route_id_list = ListOfIds()
