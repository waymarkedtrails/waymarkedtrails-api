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

On Ubuntu/Debian, the following command should install all required
dependencies:

    sudo apt install python3-numpy python3-scipy python3-gdal \
                     python3-falcon python3-slugify


The hug package in Debian is too old. You need to get it via pip instead.
If you haven't done so yet, create a virtual environment for waymarkedtrails
and enter it:

    virtualenv -p python3 --system-site-packages wmtenv
    . wmtenv/bin/activate

Then install hug:

    pip install hug

The wmt_api pacckage can simply be installed with pip:

    pip install .


Running the API
===============

The API needs a database provided by the waymarkedtrails-backend package.
See its documentation how to set up the database.

The API is a WSGI application. Run it with your favourite WSGI server.
Set the WMT_CONFIG environment variable to choose the flavour.

For example, to run the waymarkedtrails API for the hiking map with
[uwsgi](https://uwsgi-docs.readthedocs.io/en/latest/) for development purposes.
First install uwsgi:

    sudo apt install uwsgi-plugin-python3

Then run the API in development mode:

    export WMT_CONFIG=hiking
    uwsgi --plugin python3 --py-auto-reload 1 --socket 127.0.0.1:8080 --protocol=http --wsgi wmt_api.frontend

To set up uwsgi for production, please consult its documentation.

_Warning:_ the code is not compatible with ujson. If you get an error message

    TypeError: 'Type[ujson] is not Serializable'

then either make sure that `ujson` is not installed in your virtualenv or
force hug to use the built-in json library by setting the environment variable
`HUG_USE_UJSON` to the empty value:

    export HUG_USE_UJSON=

License
=======

The source code is available under GPLv3. See COPYING for more information.
