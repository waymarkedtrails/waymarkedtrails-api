import hug

from . import relation

@hug.extend_api('/relation/{oid}')
def relation_details():
    return [relation]
