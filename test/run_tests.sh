#!/bin/bash

export PYTHONPATH=..:../../waymarkedtrails-backend:../../waymarkedtrails-shields:../../osgende

if [ "x$1" == "x-n" ]; then
    shift
    pytest "$@"
elif [ "x$1" == "x-s" ]; then
    shift
    pg_virtualenv -s pytest "$@"
else
    pg_virtualenv pytest "$@"
fi
