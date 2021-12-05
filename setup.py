# SPDX-License-Identifier: GPL-3.0-only
# This file is part of the Waymarkedtrails Project
# Copyright (C) 2021 Sarah Hoffmann

from setuptools import setup

with open('README.md', 'r') as descfile:
    long_description = descfile.read()


setup(name='waymarkedtrails-api',
      description='Rest API for the Waymarkedtrails project.',
      long_description=long_description,
      version='0.1',
      maintainer='Sarah Hoffmann',
      maintainer_email='lonvia@denofr.de',
      url='https://github.com/waymarkedtrails/waymarkedtrails-api',
      license='GPL 3.0',
      packages=['wmt_api',
                'wmt_api.common',
                'wmt_api.api',
                'wmt_api.api.listings',
                'wmt_api.api.details',
                'wmt_api.api.tiles',
                'wmt_api.output'
               ],
      scripts=['wmt-api-frontend.py'],
      python_requires = ">=3.7",
      )
