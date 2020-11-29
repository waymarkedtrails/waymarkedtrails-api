# SPDX-License-Identifier: GPL-3.0-only
#
# This file is part of the Waymarked Trails Map Project
# Copyright (C) 2020 Sarah Hoffmann

from wmt_api.common.directive import parse_language_header

def test_parse_language_header_empty():
    assert parse_language_header(None) == []
    assert parse_language_header('') == []

def test_parse_language_header_simple():
    assert parse_language_header('en') == ['en']
    assert parse_language_header('de,en') == ['de', 'en']
    assert parse_language_header('en-US,en') == ['en']

def test_parse_language_header_with_quality():
    assert parse_language_header('en,fr;q=0.2,es-ES;q=0.8') == ['en', 'es', 'fr']
    assert parse_language_header('ch;q=0.5,en') == ['en', 'ch']

def test_parse_language_headerinvalid():
    assert parse_language_header('en;q=-1') == []
    assert parse_language_header('fr;q=0.0') == []
    assert parse_language_header('ch_TH') == ['ch_TH']
