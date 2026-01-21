# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of the Waymarked Trails Map Project
# Copyright (C) 2025 Sarah Hoffmann
import pytest
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy.engine.url import URL

from wmt_api.common.context import Context


@pytest.fixture
def mock_config():
    """Mock wmt_db.config module"""
    config = Mock()
    config.DB_NAME = 'test_db'
    config.DB_USER = 'test_user'
    config.DB_PASSWORD = 'test_password'
    config.MAPTYPE = 'routes'
    config.ROUTES = Mock()
    config.ROUTES.symbols = []
    config.SYMBOLS = Mock()
    return config


@pytest.fixture
def mock_mapdb_pkg():
    """Mock mapdb package"""
    pkg = Mock()
    pkg.create_mapdb = Mock(return_value=Mock())
    return pkg


def test_context_url_without_host(mock_config, mock_mapdb_pkg):
    """Test that Context creates URL without host when DB_HOST is not set"""
    with patch('wmt_api.common.context.importlib.import_module') as mock_import:
        # Setup mocks
        def import_side_effect(name):
            if 'wmt_db.config' in name:
                return mock_config
            elif 'wmt_db.maptype' in name:
                return mock_mapdb_pkg
            elif 'wmt_local_config.api' in name:
                raise ModuleNotFoundError()
            return MagicMock()

        mock_import.side_effect = import_side_effect

        # Create context without DB_HOST
        context = Context('hiking')

        # Verify URL has no host (defaults to localhost via psycopg)
        url = context.engine.url
        assert url.database == 'test_db'
        assert url.username == 'test_user'
        assert url.password == 'test_password'
        assert url.host is None  # Not explicitly set


def test_context_url_with_host(mock_config, mock_mapdb_pkg):
    """Test that Context creates URL with host when DB_HOST is set"""
    mock_config.DB_HOST = 'postgres-server'

    with patch('wmt_api.common.context.importlib.import_module') as mock_import:
        # Setup mocks
        def import_side_effect(name):
            if 'wmt_db.config' in name:
                return mock_config
            elif 'wmt_db.maptype' in name:
                return mock_mapdb_pkg
            elif 'wmt_local_config.api' in name:
                raise ModuleNotFoundError()
            return MagicMock()

        mock_import.side_effect = import_side_effect

        # Create context with DB_HOST
        context = Context('hiking')

        # Verify URL includes host
        url = context.engine.url
        assert url.database == 'test_db'
        assert url.username == 'test_user'
        assert url.password == 'test_password'
        assert url.host == 'postgres-server'


def test_context_url_with_empty_host(mock_config, mock_mapdb_pkg):
    """Test that empty DB_HOST is treated as None"""
    mock_config.DB_HOST = ''

    with patch('wmt_api.common.context.importlib.import_module') as mock_import:
        # Setup mocks
        def import_side_effect(name):
            if 'wmt_db.config' in name:
                return mock_config
            elif 'wmt_db.maptype' in name:
                return mock_mapdb_pkg
            elif 'wmt_local_config.api' in name:
                raise ModuleNotFoundError()
            return MagicMock()

        mock_import.side_effect = import_side_effect

        # Create context with empty DB_HOST
        context = Context('hiking')

        # Verify URL has no host (empty string is falsy)
        url = context.engine.url
        assert url.host is None
