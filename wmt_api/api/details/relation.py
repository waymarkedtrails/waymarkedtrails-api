import hug

@hug.get('/')
def info(oid):
    "Return general information about the route."
    return { 'id' : oid }

@hug.get()
def wikilink(oid):
    "Return a redirct into the Wikipedia page with further information."
    raise hug.HTTPNotFound()

@hug.get('/geometry/{geomtype}')
def geojson(oid, geomtype : hug.types.one_of(('geojson', 'kml', 'gpx'))):
    "Return the geometry of the function as geojson."
    return geomtype


@hug.get()
def elevation(oid):
    "Return the elevation profile of the route."
    return "TODO"
