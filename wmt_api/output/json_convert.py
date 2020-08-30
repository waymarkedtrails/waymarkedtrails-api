# SPDX-License-Identifier: GPL-3.0-only
#
# This file is part of the Waymarked Trails Map Project
# Copyright (C) 2020 Sarah Hoffmann

import hug

class JsonSerializable(object):

    def to_json_serializable(self):
        raise RuntimeError("Serialization function not implemented.")

@hug.output_format.json_convert(JsonSerializable)
def json_serializer(item):
    return item.to_json_serializable()
