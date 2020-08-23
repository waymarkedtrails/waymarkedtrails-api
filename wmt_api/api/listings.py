import hug

@hug.type(extend=hug.types.text)
def bbox_type(value):
    "A bounding box of the form: `x1, y2, x2, y2`."
    return value

@hug.get()
def by_area(bbox: bbox_type, limit: hug.types.in_range(1, 100) = 20):
    """ Return an list of routes within the given area. `bbox` describes the
        area given, `limit` describes the maximum number of results.
    """
    return "TODO"

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
