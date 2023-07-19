# SPDX-License-Identifier: GPL-3.0-only
#
# This file is part of the Waymarked Trails Map Project
# Copyright (C) 2012-2013 Espen Oldeman Lund
# Copyright (C) 2020-2023 Sarah Hoffmann

from math import ceil, fabs
from collections import OrderedDict

from osgeo import gdal
import numpy
from scipy.ndimage import map_coordinates

def round_elevation(ele, base=5):
    return int(base * round(float(ele)/base))


#
# Code from http://stackoverflow.com/questions/5515720/python-smooth-time-series-data
#
def smooth_list(x, window_len=7, window='hanning'):
    if len(x) <= window_len:
        return x

    s = numpy.r_[2 * x[0] - x[window_len-1::-1], x, 2*x[-1] - x[-1:-window_len:-1]]
    if window == 'flat': #moving average
        w = numpy.ones(window_len, 'd')
    else:
        w = getattr(numpy, window)(window_len)

    y = numpy.convolve(w/w.sum(), s, mode='same')

    return y[window_len:-window_len+1]


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


class RouteElevation:
    """ Collect and format the elevation profile for a single route.
    """
    def __init__(self, oid, dem_file, bounds):
        self.elevation = OrderedDict(id=oid, ascent=0, descent=0,
                                     end_position=0,
                                     min_elevation=None, max_elevation=None,
                                     segments=[])
        dem = Dem(str(dem_file.resolve()))
        self.band_array, self.xmax, self.ymin, self.xmin, self.ymax = \
                                                    dem.raster_array(bounds)

    def as_dict(self):
        return self.elevation

    def _add_ascent(self, elev):
        """ Calculate accumulated ascent and descent.
            Slightly complicated by the fact that we have to jump over voids.
        """
        accuracy = 15
        former_height = None
        first_valid = None
        last_valid = None
        accumulated_ascent = 0
        for x in range (1, len(elev)-1):
            current_height = elev[x]
            if not numpy.isnan(current_height):
                last_valid = current_height
                if former_height is None:
                    former_height = current_height
                    first_valid = current_height
                else:
                    if (elev[x-1] < current_height > elev[x+1]) or \
                            (elev[x-1] > current_height < elev[x+1]):
                        diff = current_height - former_height
                        if fabs(diff) > accuracy:
                            if diff > accuracy:
                                accumulated_ascent += diff
                            former_height = current_height
                        else:
                            former_height = min(former_height, current_height)

        if last_valid is None:
            # looks like the route is completely within a void
            return

        # collect the final point
        diff = last_valid - former_height
        if diff > accuracy:
            accumulated_ascent += diff

        self.elevation['ascent'] += round_elevation(accumulated_ascent)
        self.elevation['descent'] += round_elevation(accumulated_ascent
                                                     - (last_valid - first_valid))


    def add_segment(self, xcoord, ycoord, pos):
        """ Add a continuous piece of route to the elevation outout.
        """
        # Turn these into arrays of x & y coords
        xi = numpy.array(xcoord, dtype=float)
        yi = numpy.array(ycoord, dtype=float)

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
        elev = smooth_list(map_coordinates(self.band_array, [yi, xi], order=1))

        self._add_ascent(elev)

        elepoints = []
        for x, y, ele, p in zip(xcoord, ycoord, elev, pos):
            elepoints.append(OrderedDict(x=x, y=y, ele=float(ele), pos=p))
            if ele < (self.elevation['min_elevation'] or 10000):
                self.elevation['min_elevation'] = ele
            if ele > (self.elevation['max_elevation'] or -10000):
                self.elevation['max_elevation'] = ele

        if pos[-1] > self.elevation['end_position']:
            self.elevation['end_position'] = pos[-1]

        self.elevation['segments'].append({'elevation' : elepoints})

