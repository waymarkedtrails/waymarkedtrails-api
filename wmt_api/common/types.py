# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of the Waymarked Trails Map Project
# Copyright (C) 2023 Sarah Hoffmann


class Bbox:

    def __init__(self, x1, y1, x2, y2):
        self.minx = min(x1, x2)
        self.maxx = max(x1, x2)
        self.miny = min(y1, y2)
        self.maxy = max(y1, y2)


    def as_sql(self):
        return 'SRID=3857;POLYGON(({0} {1},{0} {3},{2} {3},{2} {1},{0} {1}))'\
                  .format(self.minx, self.miny, self.maxx, self.maxy)


    def write_json(self, writer):
        writer.start_array().float(self.minx, 8).next().float(self.miny, 8).next()
        writer.float(self.maxx, 8).next().float(self.maxy, 8).end_array()
