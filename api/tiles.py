import hug

@hug.get('/{zoom}/{x}/{y}.json')
def vector_tile(zoom: hug.types.in_range(12, 13),
                x: hug.types.number, y: hug.types.number):
    "Return a vector tile with the route data."
    return "TODO"
