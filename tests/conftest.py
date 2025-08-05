import pytest
import os
from unittest.mock import patch, MagicMock
from sharepoint_api.config import SharepointConfig


@pytest.fixture(scope="session", autouse=True)
def setup_test_env():
    """Set up test environment variables"""
    # Set environment variables for testing
    os.environ["SHAREPOINT_TENANT_ID"] = "test-tenant-id"
    os.environ["SHAREPOINT_CLIENT_ID"] = "test-client-id"
    os.environ["SHAREPOINT_CLIENT_SECRET"] = "test-client-secret"
    os.environ["SHAREPOINT_RESOURCE_URL"] = "https://graph.microsoft.com/"
    os.environ["SHAREPOINT_RESOURCE_URL_VERSION"] = "v1.0"

    yield

    # Clean up environment variables
    del os.environ["SHAREPOINT_TENANT_ID"]
    del os.environ["SHAREPOINT_CLIENT_ID"]
    del os.environ["SHAREPOINT_CLIENT_SECRET"]
    del os.environ["SHAREPOINT_RESOURCE_URL"]
    del os.environ["SHAREPOINT_RESOURCE_URL_VERSION"]


@pytest.fixture
def test_config():
    """Return a test SharepointConfig"""
    return SharepointConfig(
        tenant_id="test-tenant-id",
        client_id="test-client-id",
        client_secret="test-client-secret",
        resource_url="https://graph.microsoft.com/",
        resource_url_version="v1.0"
    )


@pytest.fixture
def mock_env_config():
    """Return a SharepointConfig from environment variables"""
    with patch.dict(os.environ, {
        "SHAREPOINT_TENANT_ID": "env-tenant-id",
        "SHAREPOINT_CLIENT_ID": "env-client-id",
        "SHAREPOINT_CLIENT_SECRET": "env-client-secret",
        "SHAREPOINT_RESOURCE_URL": "https://env-graph.microsoft.com/",
        "SHAREPOINT_RESOURCE_URL_VERSION": "v1.0"
    }):
        yield SharepointConfig.from_env()
