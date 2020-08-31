# SPDX-License-Identifier: GPL-3.0-only
#
# This file is part of the Waymarked Trails Map Project
# Copyright (C) 2020 Sarah Hoffmann

import hug
from io import StringIO

@hug.format.content_type('application/json')
def format_as_geojson(data, request=None, response=None):
    """ Converts the data in to geoJSON. The data is expected to be an array
        of tuples (id, geometry). The id will be added as a property id to
        the feature. The geometry must already be GeoJSON and is added verbatim.
    """
    outstr = StringIO()

    outstr.write("""{"type": "FeatureCollection",
                     "crs": {"type": "name", "properties": {"name": "EPSG:3857"}},
                     "features": [""")

    sep = ''
    for d in data:
        outstr.write(f'{sep}{{"type": "Feature", "id" : "{d[0]}", "geometry" : {d[1]}}}')
        sep = ','

    outstr.write("]}")

    return outstr.getvalue().encode('utf-8')
