# SPDX-License-Identifier: GPL-3.0-only
#
# This file is part of the Waymarked Trails Map Project
# Copyright (C) 2020 Sarah Hoffmann

import hug
from slugify import slugify
import xml.etree.ElementTree as ET
from datetime import datetime
from geoalchemy2.shape import to_shape

class RouteGeometry(object):
    """ Formats output of a geometry for a single route.

        Use together with the `format_object` formatter.
    """

    def __init__(self, obj, locales, fmt):
        self.obj = obj
        self.locales = locales
        self.to_string = getattr(self, 'to_string_' + fmt)

    def get_locale_name(self):
        for l in self.locales:
            if l in self.obj.intnames:
                return self.obj.intnames[l]

        return self.obj.name or self.obj.ref or str(self.obj.id)

    def to_string_geojson(self, request=None, response=None):
        if response is not None:
            response.content_type = "application/json; charset=utf-8"

        return f"""\
         {{ "type": "FeatureCollection",
            "crs": {{ "type": "name",
                    "properties": {{ "name": "EPSG:3857"}}
                   }},
            "features": [{{ "type": "Feature", "geometry" : {self.obj.geom} }}]
         }}"""


    def to_string_gpx(self, request=None, response=None):
        name = self.get_locale_name()

        if response is not None:
            response.content_type = "application/gpx+xml"
            response.set_header('Content-Disposition',
                                f'attachment; filename={slugify(name)}.gpx')

        root = ET.Element('gpx',
                          { 'xmlns' : "http://www.topografix.com/GPX/1/1",
                            'creator' : "waymarkedtrails.org",
                            'version' : "1.1",
                            'xmlns:xsi' : "http://www.w3.org/2001/XMLSchema-instance",
                            'xsi:schemaLocation' :  "http://www.topografix.com/GPX/1/1 http://www.topografix.com/GPX/1/1/gpx.xsd"
                           })
        # metadata
        meta = ET.SubElement(root, 'metadata')
        ET.SubElement(meta, 'name').text = name

        copy = ET.SubElement(meta, 'copyright', author='OpenStreetMap and Contributors')
        ET.SubElement(copy, 'license').text = 'http://www.openstreetmap.org/copyright'

        if request is not None:
            link = ET.SubElement(
                    meta, 'link',
                    href=request.uri)
            ET.SubElement(link, 'text').text = 'Waymarked Trails'

        ET.SubElement(meta, 'time').text = datetime.utcnow().isoformat()

        # and the geometry
        trk = ET.SubElement(root, 'trk')
        geom = to_shape(self.obj.geom)

        if geom.geom_type == 'LineString':
            geom = (geom,)

        for line in geom:
            seg = ET.SubElement(trk, 'trkseg')
            for pt in line.coords:
                ET.SubElement(seg, 'trkpt', lat=f'{pt[1]:.7f}', lon=f'{pt[0]:.7f}')

        return '<?xml version="1.0" encoding="UTF-8" standalone="no" ?>\n\n'.encode('utf-8')\
               + ET.tostring(root, encoding='UTF-8')

    def to_string_kml(self, request=None, response=None):
        name = self.get_locale_name()

        if response is not None:
            response.content_type = 'application/vnd.google-earth.kml+xml'
            response.set_header('Content-Disposition',
                                f'attachment; filename={slugify(name)}.kml')

        root = ET.Element('kml',
                          { 'xmlns' : "http://www.opengis.net/kml/2.2",
                            'creator' : "waymarkedtrails.org",
                            'version' : "1.1",
                            'xmlns:atom' : "http://www.w3.org/2005/Atom"
                           })
        # metadata
        doc = ET.SubElement(root, 'Document')
        ET.SubElement(doc, 'name').text = name
        ET.SubElement(doc, 'atom:author').text = 'waymarkedtrails.org; OpenStreetMap and Contributors http://www.openstreetmap.org/copyright'

        if request is not None:
            ET.SubElement(doc, 'atom:link', {'href' : request.uri})

        mark = ET.SubElement(doc, 'Placemark')
        ET.SubElement(mark, 'name').text = name

        # and the geometry
        multi = ET.SubElement(mark, 'MultiGeometry')

        geom = to_shape(self.obj.geom)

        if geom.geom_type == 'LineString':
            geom = (geom,)

        for line in geom:
            linestring = ET.SubElement(multi, 'LineString')
            ET.SubElement(linestring, 'coordinates').text = \
              '\n'.join((f'{pt[0]:.7f},{pt[1]:.7f}' for pt in line.coords))

        return '<?xml version="1.0" encoding="UTF-8" ?>\n\n'.encode('utf-8') \
                 + ET.tostring(root, encoding="UTF-8")
