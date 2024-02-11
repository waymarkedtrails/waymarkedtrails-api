# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of the Waymarked Trails Map Project
# Copyright (C) 2024 Sarah Hoffmann
from ...common.router import Router
from ..details.relation import APIDetailsRelation
from ..details.guidepost import APIDetailsGuidepost

class APIDetails(Router):

    def __init__(self, context):
        super().__init__(context)
        self.relations_api = APIDetailsRelation(context)
        self.guidepost_api = APIDetailsGuidepost(context)

    def add_routes(self, app, base):
        self.relations_api.add_routes(app, base + '/relation')
        self.guidepost_api.add_routes(app, base + '/guidepost')
