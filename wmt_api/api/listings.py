import hug
from collections import OrderedDict

from ..db.directive import connection, routes_table
from ..common.types import bbox_type

hug.defaults.cli_output_format = hug.output_format.json



def create_route_list(qkey, qvalue, res):
    out = OrderedDict()
    out[qkey] = qvalue
    #out['symbol_url'] = '%(MEDIA_URL)s/symbols/%(BASENAME)s/' % (
    #                       cherrypy.request.app.config['Global'])
    #out['results'] = [api.common.RouteDict(r) for r in res]

    return out

@hug.get()
@hug.cli()
def by_area(conn: connection, status: routes_table,
            bbox: bbox_type, limit: hug.types.in_range(1, 100) = 20):
    """ Return the list of routes within the given area. `bbox` describes the
        area given, `limit` describes the maximum number of results.
    """
    print(str(bbox))
    print(str(limit))
    return create_route_list('bbox', bbox, None)

@hug.get()
def by_ids(ids: hug.types.delimited_list(',')):
    """ Return route overview information by relation id.
    """
    return "TODO"

@hug.get()
def search(query: hug.types.text, limit: hug.types.in_range(1, 100) = 20,
           page: hug.types.in_range(1, 10) = 1):
    """ Search a route by name.
    """
    return "TODO"

@hug.get()
def segments(bbox: bbox_type, ids: hug.types.delimited_list(',')):
    """ Return the geometry of the routes `ids` that intersect with the
        boundingbox `bbox`. If the route goes outside the box, the geometry
        is cut accordingly.
    """
    return "TODO"
