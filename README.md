Waymarked Trails - API frontend
===============================

[Waymarked Trails](https://waymarkedtrails.org) is a website that shows
recreational routes from [OpenStreetMap](https://openstreetmap.org) and
lets you inspect the routes and selected details.

This repository contains the API frontend. It is implemented with
[hug](https://www.hug.rest/).

Installation
============

The API depends on the following packages:

 * [hug](https://www.hug.rest/)
 * [osgende](https://github.com/waymarkedtrails/osgende)
 * [waymarkedtrails-backend](https://github.com/waymarkedtrails/waymarkedtrails-backend)

For the elevation profiles these additional packages are needed:

 * [Numpy](https://numpy.org/)
 * [Scipy](https://scipy.org/)
 * [GDAL with Python bindings](https://gdal.org/api/python.html)

The wmt_api pacckage can simply be installed with pip:

    pip install .


Running the API
===============

The API needs a database provided by the waymarkedtrails-backend package.
See its documentation how to set up the database.

The API is a WSGI application. Run it with your favourite WSGI server.
Set the WMT_CONFIG environment variable to choose the flavour.

For example, to run the waymarkedtrails API for the hiking map with
[uwsgi](https://uwsgi-docs.readthedocs.io/en/latest/) for development purposes:

    export WMT_CONFIG=hiking
    uwsgi --plugin python3 --py-auto-reload 1 --socket 127.0.0.1:8080 --protocol=http --wsgi wmt_api.frontend

License
=======

The source code is available under GPLv3. See COPYING for more information.
