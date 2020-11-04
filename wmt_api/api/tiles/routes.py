import hug
import sqlalchemy as sa
from io import StringIO

from ...common import directive
from ...common.types import Bbox
from ...common.formatter import format_as_geojson

# constants for bbox computation for level 12
MAPWIDTH = 20037508.34
TILEWIDTH = MAPWIDTH/(2**11)

@hug.get('/{zoom}/{x}/{y}.json', output=format_as_geojson)
def vector_tile(conn: directive.connection, tables: directive.tables,
                zoom: hug.types.in_range(12, 13),
                x: hug.types.in_range(0, 2**12),
                y: hug.types.in_range(0, 2**12)):
    "Return a vector tile with the route data."

    b = Bbox((x * TILEWIDTH - MAPWIDTH, MAPWIDTH - (y + 1) * TILEWIDTH,
             (x + 1) * TILEWIDTH - MAPWIDTH, MAPWIDTH - y * TILEWIDTH))

    # JSON header
    out = StringIO()
    out.write("""{ "type": "FeatureCollection",
                    "crs": {"type": "name", "properties": {"name": "EPSG:3857"}},
                    "features": [""")

    # Route ways
    d = tables.style.data
    q = sa.select([sa.literal('way').label('type'), d.c.toprels.label('top_relations'),
                   d.c.cldrels.label('child_relations'),
                   d.c.inrshields.concat(d.c.lshields).label('shields'),
                   d.c.style, d.c['class'],
                   d.c.geom.ST_Intersection(b.as_sql()).ST_AsGeoJSON().label('geometry')])\
          .where(d.c.geom.intersects(b.as_sql()))\
          .order_by(d.c.id)


    elements = list(conn.execute(q))

    # Guideposts
    if hasattr(tables, 'guideposts'):
        d = tables.guideposts.data
        q = sa.select([sa.literal('guidepost').label('type'),
                       d.c.id.label('osm_id'), d.c.name, d.c.ele,
                       d.c.geom.ST_AsGeoJSON().label('geometry')])\
                .where(d.c.geom.intersects(b.as_sql()))\
                .order_by(d.c.id)

        elements.extend(conn.execute(q))

    return elements
