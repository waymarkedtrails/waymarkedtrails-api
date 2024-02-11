# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of the Waymarked Trails Map Project
# Copyright (C) 2024 Sarah Hoffmann
from ...common.router import Router
from ..details.relation import APIDetailsRelation
from ..details.way import APIDetailsWay
from ..details.wayset import APIDetailsWayset

class APIDetails(Router):

    def __init__(self, context):
        super().__init__(context)
        self.relations_api = APIDetailsRelation(context)
        self.way_api = APIDetailsWay(context)
        self.wayset_api = APIDetailsWayset(context)

    def add_routes(self, app, base):
        self.relations_api.add_routes(app, base + '/relation')
        self.way_api.add_routes(app, base + '/way')
        self.wayset_api.add_routes(app, base + '/wayset')
