# SPDX-License-Identifier: GPL-3.0-only
#
# This file is part of the Waymarked Trails Map Project
# Copyright (C) 2024 Sarah Hoffmann

import json
import urllib.request
from urllib.parse import quote
from osgende.common.tags import TagStore

WIKIPEDIA_BASEURL = 'https://{}.wikipedia.org/wiki/{}'
WIKIPEDIA_TRANSLATEURL = 'https://{}.wikipedia.org/w/api.php?action=query&prop=langlinks&titles={}&llprop=url&&lllang={}&format=json'

def get_wikipedia_link(tags, locales):
    """ Create a wikipedia link from a list of OSM tags. It scans for
        wikipedia tags and reformats them to form a full URL.
        Wikipedia tags with URLs already formed are not accepted.
    """
    wikientries = TagStore(tags or {}).get_wikipedia_tags()

    if not wikientries:
        return None

    for lang in locales:
        if lang in wikientries:
            title = quote(wikientries[lang].replace(' ', '_'))
            return WIKIPEDIA_BASEURL.format(lang, title)

        for k, v in wikientries.items():
            url = WIKIPEDIA_TRANSLATEURL.format(k, quote(v.encode('utf8')), lang)
            try:
                req = urllib.request.Request(url, headers={
                    'User-Agent' : 'waymarkedtrails.org'
                    })
                data = urllib.request.urlopen(req).read().decode('utf-8')
                data = json.loads(data)
            except:
                continue # oh well, we tried
            (pgid, data) = data["query"]["pages"].popitem()
            if 'langlinks' in data:
                return data['langlinks'][0]['url']
    else:
        # given up to find a requested language
        k, v = wikientries.popitem()
        return WIKIPEDIA_BASEURL.format(k, quote(v.replace(' ', '_')))
