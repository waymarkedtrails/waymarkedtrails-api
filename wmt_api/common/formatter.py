# SPDX-License-Identifier: GPL-3.0-only
#
# This file is part of the Waymarked Trails Map Project
# Copyright (C) 2020 Sarah Hoffmann

import json
from io import StringIO

import hug

@hug.output_format.on_valid('application/json')
def format_as_geojson(data, request=None, response=None):
    """ Convert the data in to geoJSON. The data is expected to be an array
        of tuples (id, geometry). The id will be added as a property id to
        the feature. The geometry must already be GeoJSON and is added verbatim.
    """
    outstr = StringIO()

    outstr.write("""{"type": "FeatureCollection",
                     "crs": {"type": "name", "properties": {"name": "EPSG:3857"}},
                     "features": [""")

    sep = ''
    for d in data:
        outstr.write(f'{sep}{{"type": "Feature", "geometry" : {d.geometry}')
        if 'id' in d.keys():
            outstr.write(f', "id" : "{d.id}"')
        if len(d.keys()) > 2:
            outstr.write(', "properties" : ')
            json.dump({ k: d[k] for k in d.keys() if k not in ('id', 'geometry')},
                      outstr)
        outstr.write('}')
        sep = ','

    outstr.write("]}")

    return outstr.getvalue().encode('utf-8')

@hug.output_format.content_type("application/json")
def format_as_redirect(data, request=None, response=None):
    if data is None:
        raise hug.HTTPNotFound()

    raise hug.HTTPTemporaryRedirect(data)

@hug.output_format.content_type("file/dynamic")
def format_object(data, request=None, response=None):
    output = data.to_string(request=request, response=response)

    if isinstance(output, str):
        output.encode('utf-8')

    return output
