Waymarked Trails - API frontend
===============================

[Waymarked Trails](https://waymarkedtrails.org) is a website that shows
recreational routes from [OpenStreetMap](https://openstreetmap.org) and
lets you inspect the routes and selected details.

This repository contains the API frontend. It is implemented with
[falcon](https://falconframework.org/).

Installation
============

The API depends on the following packages:

 * [falcon](https://falconframework.org/)
 * [osgende](https://github.com/waymarkedtrails/osgende)
 * [waymarkedtrails-backend](https://github.com/waymarkedtrails/waymarkedtrails-backend)
 * [psycopg3](https://www.psycopg.org/psycopg3/)
 * [aoifiles](https://pypi.org/project/aiofiles/)

For the elevation profiles these additional packages are needed:

 * [Numpy](https://numpy.org/)
 * [Scipy](https://scipy.org/)
 * [GDAL with Python bindings](https://gdal.org/api/python.html)

On Ubuntu/Debian, the following command should install all required
dependencies:

    sudo apt install python3-numpy python3-scipy python3-gdal \
                     python3-falcon python3-slugify


The wmt_api pacckage can simply be installed with pip:

    pip install .

Adding indexes for faster search
================================

The search API uses a trigram search for fuzzy searching. You can speed this
up by creating an index, e.g. for hiking routes:

```
CREATE INDEX idx_route_trgrm ON hiking.routes USING GIST ((name || jsonb_path_query_array(intnames, '$.*')) gist_trgm_ops);
```

Running the API
===============

The API needs a database provided by the waymarkedtrails-backend package.
See its documentation how to set up the database.

The API is a ASGI application. Run it with your favourite ASGI server.
Set the WMT_CONFIG environment variable to choose the flavour.

The following describes how to run the waymarkedtrails API for the hiking map with
[uvicorn](https://www.uvicorn.org/) for development purposes.
First install uvicorn:

    sudo apt install uvicorn

Then run the API in development mode:

    export WMT_CONFIG=hiking
    uvicorn --port 8080 wmt_api.frontend:app

To set up uvicorn for production, please consult its documentation.

License
=======

The source code is available under GPLv3. See COPYING for more information.
