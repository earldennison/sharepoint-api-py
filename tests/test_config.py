import pytest
import os
from unittest.mock import patch
from sharepoint_api.config import SharepointConfig
from unittest.mock import MagicMock
import dotenv
import pathlib
import yaml


class TestSharepointConfig:

    def test_init(self):
        config = SharepointConfig(
            tenant_id="test-tenant-id",
            client_id="test-client-id",
            client_secret="test-client-secret",
            resource_url="https://graph.microsoft.com/",
            resource_url_version="v1.0"
        )

        assert config.tenant_id == "test-tenant-id"
        assert config.client_id == "test-client-id"
        assert config.client_secret == "test-client-secret"
        assert config.resource_url == "https://graph.microsoft.com/"
        assert config.resource_url_version == "v1.0"

    def test_from_env(self):
        with patch.dict(os.environ, {
            "SHAREPOINT_TENANT_ID": "env-tenant-id",
            "SHAREPOINT_APP_ID": "env-client-id",
            "SHAREPOINT_APP_SECRET": "env-client-secret"
        }, clear=True):
            config = SharepointConfig.from_env()

            assert config.tenant_id == "env-tenant-id"
            assert config.client_id == "env-client-id"
            assert config.client_secret == "env-client-secret"
            assert config.resource_url == "https://graph.microsoft.com/"
            assert config.resource_url_version == "v1.0"

    def test_from_env_missing_values(self):
        with patch.dict(os.environ, {
            "SHAREPOINT_TENANT_ID": "env-tenant-id",
            # Missing SHAREPOINT_APP_ID
            "SHAREPOINT_APP_SECRET": "env-client-secret"
        }, clear=True):
            with pytest.raises(AssertionError):
                SharepointConfig.from_env()

    def test_from_env_file(self):
        # Test from_env_file class method (uses from_env indirectly)
        with patch('os.path.exists', return_value=True), \
                patch('dotenv.load_dotenv'), \
                patch.object(SharepointConfig, 'from_env') as mock_from_env:

            mock_config = MagicMock()
            mock_from_env.return_value = mock_config

            result = SharepointConfig.from_env_file()

            # Verify load_dotenv was called and from_env was used
            assert result is mock_config
            mock_from_env.assert_called_once()

    def test_from_env_file_file_not_found(self):
        # Test with file not found
        with patch('pathlib.Path.exists', return_value=False):
            with pytest.raises(FileNotFoundError):
                SharepointConfig.from_env_file()

    def test_from_config(self):
        # Test from_config class method with a YAML file
        test_config = {
            "tenant_id": "config-tenant-id",
            "client_id": "config-client-id",
            "client_secret": "config-client-secret",
            "resource_url": "https://config-graph.microsoft.com/",
            "resource_url_version": "v2.0"
        }

        with patch('os.path.exists', return_value=True), \
                patch('builtins.open'), \
                patch('yaml.safe_load', return_value=test_config):

            config = SharepointConfig.from_config()

            assert config.tenant_id == "config-tenant-id"
            assert config.client_id == "config-client-id"
            assert config.client_secret == "config-client-secret"
            assert config.resource_url == "https://config-graph.microsoft.com/"
            assert config.resource_url_version == "v2.0"

    def test_model_dump(self):
        config = SharepointConfig(
            tenant_id="test-tenant-id",
            client_id="test-client-id",
            client_secret="test-client-secret",
            resource_url="https://graph.microsoft.com/",
            resource_url_version="v1.0"
        )

        dump = config.model_dump()
        assert dump["tenant_id"] == "test-tenant-id"
        assert dump["client_id"] == "test-client-id"
        assert dump["client_secret"] == "test-client-secret"
        assert dump["resource_url"] == "https://graph.microsoft.com/"
        assert dump["resource_url_version"] == "v1.0"
