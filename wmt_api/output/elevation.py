# SPDX-License-Identifier: GPL-3.0-only
#
# This file is part of the Waymarked Trails Map Project
# Copyright (C) 2012-2013 Espen Oldeman Lund
# Copyright (C) 2025 Sarah Hoffmann
import json
from math import ceil, fabs
from collections import OrderedDict

from osgeo import gdal
import numpy
import falcon
from scipy.ndimage import map_coordinates
import sqlalchemy as sa
import geoalchemy2.functions as gf
from geoalchemy2.shape import to_shape
from geoalchemy2 import Geography
from shapely.geometry import Point, LineString

class Bbox:
    def __init__(self):
        self.minx = 30000000
        self.maxx = -30000000
        self.miny = 30000000
        self.maxy = -30000000

    def expand(self, minx, miny, maxx, maxy):
        if minx < self.minx:
            self.minx = minx
        if maxx > self.maxx:
            self.maxx = maxx
        if miny < self.miny:
            self.miny = miny
        if maxy > self.maxy:
            self.maxy = maxy

    def bounds(self):
        return (self.minx, self.miny, self.maxx, self.maxy)


def round_elevation(ele, base=5):
    return int(base * round(float(ele)/base))


#
# Code from http://stackoverflow.com/questions/5515720/python-smooth-time-series-data
# and https://stackoverflow.com/questions/9537543/replace-nans-in-numpy-array-with-closest-non-nan-value
#
def smooth_and_fill_list(x, window_len=7, window='hanning'):
    mask = numpy.isnan(x)
    x[mask] = numpy.interp(numpy.flatnonzero(mask), numpy.flatnonzero(~mask), x[~mask])

    if len(x) <= window_len:
        return x

    s = numpy.r_[2 * x[0] - x[window_len-1::-1], x, 2*x[-1] - x[-1:-window_len:-1]]
    if window == 'flat': #moving average
        w = numpy.ones(window_len, 'd')
    else:
        w = getattr(numpy, window)(window_len)

    y = numpy.convolve(w/w.sum(), s, mode='same')

    return y[window_len:-window_len+1]


async def get_way_elevation_data(conn, id_col, geom_col, where, step):
    sql = sa.select(id_col,
                    geom_col.ST_PointN(1).label('first'),
                    geom_col.ST_PointN(-1).label('last'),
                    geom_col.ST_Transform(4326).label('geom'))\
            .where(where)\
            .subquery()

    sql = sa.select(sql.c.id, sql.c.first, sql.c.last, sql.c.geom,
                    gf.ST_Length(sa.cast(sql.c.geom, Geography)).label('len'))\
            .subquery()

    sql = sa.select(sql.c.id, sql.c.len, sql.c.first, sql.c.last,
                    sa.case((sql.c.len < (step * 1.1), None),
                            else_=sql.c.geom.ST_LineInterpolatePoints(step/sql.c.len))
                                       .ST_Transform(3857).label('mid'))

    ways = []
    bbox = Bbox()
    for row in await conn.execute(sql):
        first = to_shape(row.first)
        x = [first.x]
        y = [first.y]
        if row.mid:
            mid = to_shape(row.mid)
            if mid.geom_type == 'Point':
                x.append(mid.x)
                y.append(mid.y)
            else:
                for pt in mid.geoms:
                    x.append(pt.x)
                    y.append(pt.y)
        last = to_shape(row.last)
        x.append(last.x)
        y.append(last.y)
        bbox.expand(min(x), min(y), max(x), max(y))
        ways.append({'sid': row.id, 'length': row.len, 'x': x, 'y': y})

    return ways, bbox.bounds()


class Dem:

    def __init__(self, src):
        self.source = gdal.Open(src)
        self.transform = self.source.GetGeoTransform()

    def raster_array(self, bbox):
        # Calculate pixel coordinates (rounding always toward the outside)
        ulx, uly = (int(x) for x in self.geo_to_pixel(bbox[0], bbox[3]))
        lrx, lry = (int(ceil(x)) for x in self.geo_to_pixel(bbox[2], bbox[1]))

        # Get rasterarray
        band_array = self.source.GetRasterBand(1).ReadAsArray(ulx, uly,
                                                              lrx - ulx + 1,
                                                              lry - uly + 1)

        # compute true boundaries (after rounding) of raster array
        xmax, ymax = self.pixel_to_geo(ulx, uly)
        xmin, ymin = self.pixel_to_geo(lrx, lry)

        return band_array, xmin, ymin, xmax, ymax

    def geo_to_pixel(self, x, y):
        g0, g1, g2, g3, g4, g5 = self.transform

        if g2 == 0:
            x_pixel = (x - g0) / float(g1)
            y_pixel = (y - g3 - x_pixel * g4) / float(g5)
        else:
            x_pixel = (y * g2 - x * g5 + g0 * g5 - g2 * g3) / float(g2 * g4 - g1 * g5)
            y_pixel = (x - g0 - x_pixel * g1) / float(g2)

        return x_pixel, y_pixel


    def pixel_to_geo(self, x, y):
        g0, g1, g2, g3, g4, g5 = self.transform

        if g2 == 0:
            xout = x * float(g1) + g0
            yout = float(g5) * y + float(g4) * (x - g0) / g1 + g3
        else:
            xout = g2 * y + x * g1 + float(g0)
            yout = (x * (float(g2 * g4) - float(g1 * g5)
                    + xout * g5 - g0 * g5 + g2 * g3)) / float(g2)

        return xout, yout


class SegmentElevation:
    """ Collect and format the elevation profile for a single route.
    """
    MAX_DEVIATION = 5

    def __init__(self, dem_file, bounds, max_segment_len=500):
        self.max_segment_len = max_segment_len
        self.min_ele = None
        self.max_ele = None
        self.segments = {}
        dem = Dem(str(dem_file.resolve()))
        self.band_array, self.xmax, self.ymin, self.xmin, self.ymax = \
                                                    dem.raster_array(bounds)

    def to_response(self, response):
        response.status = 200
        response.content_type = falcon.MEDIA_JSON
        response.text = json.dumps({'min_elevation': int(self.min_ele),
                                    'max_elevation': int(self.max_ele),
                                    'segments': self.segments})


    def _sum_and_filter(self, xs, ys, eles, step, total):
        max_steps = int(self.max_segment_len/step)
        start = None
        start_ele = None

        for i, x, y, ele in zip(range(len(xs)), xs, ys, eles):
            ele = float(ele)
            if ele < (self.min_ele or 10000):
                self.min_ele = ele
            if ele > (self.max_ele or -10000):
                self.max_ele = ele

            if start is None:
                start = 0
                start_ele = ele
                yield x, y, start_ele, 0
            else:
                is_last = i == len(xs) - 1
                if is_last or i >= start + max_steps or \
                   numpy.max(numpy.abs(numpy.linspace(start_ele, ele, i - start + 1)
                                        - eles[start:i + 1])) > self.MAX_DEVIATION:
                    start = i
                    start_ele = ele
                    yield x, y, start_ele, total if is_last else i * step

    def add_segment(self, sid, x, y, length, step):
        """ Add a continuous piece of route to the elevation outout.
        """
        # Turn these into arrays of x & y coords
        xi = numpy.array(x, dtype=float)
        yi = numpy.array(y, dtype=float)

        # Now, we'll set points outside the boundaries to lie along an edge
        xi[xi > self.xmax] = self.xmax
        xi[xi < self.xmin] = self.xmin
        yi[yi > self.ymax] = self.ymax
        yi[yi < self.ymin] = self.ymin

        # We need to convert these to (float) indicies
        #   (xi should range from 0 to (nx - 1), etc)
        ny, nx = self.band_array.shape
        xi = (nx - 1) * (xi - self.xmin) / (self.xmax - self.xmin)
        yi = -(ny - 1) * (yi - self.ymax) / (self.ymax - self.ymin)

        # Interpolate elevation values
        # map_coordinates does cubic interpolation by default, 
        # use "order=1" to preform bilinear interpolation
        elev = smooth_and_fill_list(map_coordinates(self.band_array, [yi, xi], order=1))

        elepoints = []
        for x, y, ele, p in self._sum_and_filter(x, y, elev, step, length):
            elepoints.append({'x': round(x, 2), 'y': round(y, 2),
                              'ele': int(ele), 'pos': round(p, 2)})
            if ele < (self.min_ele or 10000):
                self.min_ele = ele
            if ele > (self.max_ele or -10000):
                self.max_ele = ele

        self.segments[str(sid)] = {'elevation' : elepoints}

