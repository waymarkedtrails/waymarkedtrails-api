import hug

from api.details import relation

@hug.extend_api('/relation/{oid}')
def relation_details():
    return [relation]
