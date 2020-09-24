from os import path as op


PROJECT_DIR =  op.normpath(op.join(op.realpath(__file__), '../../..'))

DEM_FILE = op.join(PROJECT_DIR, 'dem/900913/earth.vrt')
