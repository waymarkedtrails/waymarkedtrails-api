# SPDX-License-Identifier: GPL-3.0-only
#
# This file is part of the Waymarked Trails Map Project
# Copyright (C) 2012-2013 Espen Oldeman Lund
# Copyright (C) 2020 Sarah Hoffmann

import hug
from collections import OrderedDict
from math import ceil, fabs

from osgeo import gdal
import numpy
from scipy.ndimage import map_coordinates

def round_elevation(x, base=5):
    return int(base * round(float(x)/base))

def compute_ascent(elev):
    """ Calculate accumulated ascent and descent.
        Slightly complicated by the fact that we have to jump over voids.
    """
    accuracy = 15
    formerHeight = None
    firstvalid = None
    lastvalid = None
    accumulatedAscent = 0
    for x in range (1, len(elev)-1):
        currentHeight = elev[x]
        if not numpy.isnan(currentHeight):
            lastvalid = currentHeight
            if formerHeight is None:
                formerHeight = currentHeight
                firstvalid = currentHeight
            else:
                if (elev[x-1] < currentHeight > elev[x+1]) or \
                        (elev[x-1] > currentHeight < elev[x+1]):
                    diff = currentHeight-formerHeight
                    if fabs(diff) > accuracy:
                        if diff > accuracy:
                            accumulatedAscent += diff
                        formerHeight = currentHeight

    if lastvalid is None:
        # looks like the route is completely within a void
        return 0, 0

    # collect the final point
    diff = lastvalid - formerHeight
    if diff > accuracy:
        accumulatedAscent += diff

    # ascent, descent
    return round_elevation(accumulatedAscent), round_elevation(accumulatedAscent - (lastvalid - firstvalid))

#
# Code from http://stackoverflow.com/questions/5515720/python-smooth-time-series-data
#
def smooth_list(x,window_len=7,window='hanning'):
    if len(x) <= window_len:
        return x

    s = numpy.r_[2*x[0] - x[window_len-1::-1], x, 2*x[-1] - x[-1:-window_len:-1]]
    if window == 'flat': #moving average
        w = numpy.ones(window_len,'d')
    else:
        w = getattr(numpy, window)(window_len)

    y = numpy.convolve(w/w.sum(), s, mode='same')

    return y[window_len:-window_len+1]



class Dem(object):

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
            xPixel = (x - g0) / float(g1)
            yPixel = (y - g3 - xPixel*g4) / float(g5)
        else:
            xPixel = (y*g2 - x*g5 + g0*g5 - g2*g3) / float(g2*g4 - g1*g5)
            yPixel = (x - g0 - xPixel*g1) / float(g2)

        return xPixel, yPixel


    def pixel_to_geo(self, x, y):
        g0, g1, g2, g3, g4, g5 = self.transform

        if g2 == 0:
            xout = x*float(g1) + g0
            yout = float(g5)*y + float(g4)*(x - g0)/g1 + g3
        else:
            xout = g2*y + x*g1 + float(g0)
            yout = (x*(float(g2*g4)-float(g1*g5)+xout*g5-g0*g5+g2*g3))/float(g2)

        return xout, yout


class RouteElevation(object):
    """ Gets and format the elevation profile for a single route.
    """
    def __init__(self, oid, dem_file, bounds):
        self.elevation = OrderedDict(id=oid, ascent=0, descent=0,
                                     end_position=0,
                                     min_elevation=None, max_elevation=None,
                                     segments=[])
        dem = Dem(dem_file)
        self.band_array, self.xmax, self.ymin, self.xmin, self.ymax = \
                                                    dem.raster_array(bounds)

    def add_segment(self, xcoord, ycoord, pos):

        # Turn these into arrays of x & y coords
        xi = numpy.array(xcoord, dtype=numpy.float)
        yi = numpy.array(ycoord, dtype=numpy.float)

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
        mapped = map_coordinates(self.band_array, [yi, xi], order=1)
        elev = smooth_list(map_coordinates(self.band_array, [yi, xi], order=1))

        a, d = compute_ascent(elev)
        self.elevation['ascent'] += a
        self.elevation['descent'] += d

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

