import pytest
import json
import os
from unittest.mock import patch, MagicMock, mock_open
import requests
from sharepoint_api.core.client import SharePointClient
from sharepoint_api.config import SharepointConfig
from sharepoint_api.errors import SharepointAPIError, AuthenticationError, ResourceNotFoundError


@pytest.fixture
def mock_config():
    return SharepointConfig(
        tenant_id="test-tenant-id",
        client_id="test-client-id",
        client_secret="test-client-secret",
        resource_url="https://graph.microsoft.com/",
        resource_url_version="v1.0"
    )


@pytest.fixture
def mock_access_token():
    return "mock-access-token"


@pytest.fixture
def mock_client(mock_config, mock_access_token):
    with patch.object(SharePointClient, 'get_access_token', return_value=mock_access_token):
        client = SharePointClient.from_config(mock_config)
        yield client


class MockResponse:
    def __init__(self, json_data, status_code=200, content=None):
        self.json_data = json_data
        self.status_code = status_code
        self.content = content if content else json.dumps(
            json_data).encode('utf-8')

    def json(self):
        return self.json_data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP Error: {self.status_code}")


class TestSharePointClient:

    def test_initialization(self, mock_config, mock_access_token):
        with patch.object(SharePointClient, 'get_access_token', return_value=mock_access_token):
            client = SharePointClient.from_config(mock_config)
            assert client.tenant_id == mock_config.tenant_id
            assert client.client_id == mock_config.client_id
            assert client.client_secret == mock_config.client_secret
            assert client.resource_url == mock_config.resource_url
            assert client.resource_url_version == mock_config.resource_url_version
            assert client.full_resource_url == f"{mock_config.resource_url}{mock_config.resource_url_version}"
            assert client.access_token == mock_access_token

    def test_get_access_token(self, mock_config):
        # Test a simpler aspect - that the method exists and formats the request correctly
        with patch('requests.post') as mock_post:
            # Configure mock to return a response with access token
            mock_post.return_value = MockResponse(
                {"access_token": "test-token"})

            # Skip constructor to avoid the initial token fetch
            client = MagicMock()
            client.oauth_url = f"https://login.microsoftonline.com/{mock_config.tenant_id}/oauth2/v2.0/token"
            client.client_id = mock_config.client_id
            client.client_secret = mock_config.client_secret
            client.resource_url = mock_config.resource_url
            client.auth_headers = {
                'Content-Type': 'application/x-www-form-urlencoded'}

            # Call the actual method directly
            token = SharePointClient.get_access_token(client)

            # Verify the token is returned correctly
            assert token == "test-token"

            # Verify request was made correctly
            mock_post.assert_called_once()
            args, kwargs = mock_post.call_args
            assert args[0] == client.oauth_url
            assert kwargs['data']['grant_type'] == 'client_credentials'
            assert kwargs['data']['client_id'] == mock_config.client_id
            assert kwargs['data']['client_secret'] == mock_config.client_secret
            assert kwargs['data']['scope'] == f"{mock_config.resource_url}.default"

    def test_get_access_token_error(self, mock_config):
        with patch('requests.post') as mock_post:
            # Create a mock response that raises an error
            mock_response = MagicMock()
            mock_response.status_code = 401
            mock_response.raise_for_status.side_effect = requests.HTTPError(
                "401 Unauthorized")
            mock_post.return_value = mock_response

            # Skip constructor to avoid the initial token fetch
            client = MagicMock()
            client.oauth_url = f"https://login.microsoftonline.com/{mock_config.tenant_id}/oauth2/v2.0/token"
            client.client_id = mock_config.client_id
            client.client_secret = mock_config.client_secret
            client.resource_url = mock_config.resource_url
            client.auth_headers = {
                'Content-Type': 'application/x-www-form-urlencoded'}

            # Test with error response
            with pytest.raises(ConnectionError):
                SharePointClient.get_access_token(client)

    def test_sites(self, mock_client):
        with patch.object(mock_client, 'get') as mock_get:
            mock_get.return_value = MockResponse(
                {"value": [{"id": "site1", "name": "Test Site"}]})
            result = mock_client.sites()
            assert result["value"][0]["id"] == "site1"
            mock_get.assert_called_once_with("/sites")

    def test_sites_with_search(self, mock_client):
        with patch.object(mock_client, 'get') as mock_get:
            mock_get.return_value = MockResponse(
                {"value": [{"id": "site1", "name": "Test Site"}]})
            result = mock_client.sites(search="Test Site")
            assert result["value"][0]["id"] == "site1"
            mock_get.assert_called_once_with(
                "/sites", params={"search": "Test Site"})

    def test_sites_with_site_id(self, mock_client):
        with patch.object(mock_client, 'get') as mock_get:
            mock_get.return_value = MockResponse(
                {"id": "site1", "name": "Test Site"})
            result = mock_client.sites(site_id="site1")
            assert result["id"] == "site1"
            mock_get.assert_called_once_with("/sites/site1")

    def test_get_sharepoint_site(self, mock_client):
        with patch.object(mock_client, 'sites') as mock_sites:
            mock_sites.return_value = {
                "value": [{"id": "site1", "name": "Test Site"}]}

            # The method returns the first item from the value array, not the entire response
            site = mock_client.get_sharepoint_site("Test Site")
            assert site["id"] == "site1"
            mock_sites.assert_called_once_with(search="Test Site")

    def test_get_sharepoint_site_not_found(self, mock_client):
        with patch.object(mock_client, 'sites') as mock_sites:
            mock_sites.return_value = {"value": []}
            with pytest.raises(ResourceNotFoundError):
                mock_client.get_sharepoint_site("Nonexistent Site")

    def test_get_sharepoint_site_invalid_response(self, mock_client):
        with patch.object(mock_client, 'sites') as mock_sites:
            mock_sites.return_value = {"invalid_key": "invalid_value"}
            with pytest.raises(ResourceNotFoundError):
                mock_client.get_sharepoint_site("Test Site")

    def test_get_sharepoint_site_api_error(self, mock_client):
        with patch.object(mock_client, 'sites') as mock_sites:
            mock_sites.side_effect = SharepointAPIError("API Error")
            with pytest.raises(SharepointAPIError):
                mock_client.get_sharepoint_site("Test Site")

    def test_get_sharepoint_site_unknown_error(self, mock_client):
        with patch.object(mock_client, 'sites') as mock_sites:
            mock_sites.side_effect = Exception("Unknown Error")
            with pytest.raises(SharepointAPIError):
                mock_client.get_sharepoint_site("Test Site")

    def test_drives(self, mock_client):
        with patch.object(mock_client, 'get') as mock_get:
            mock_get.return_value = MockResponse(
                {"value": [{"id": "drive1", "name": "Test Drive"}]})
            result = mock_client.drives("site1")
            assert result["value"][0]["id"] == "drive1"
            mock_get.assert_called_once_with("/sites/site1/drives")

    def test_drives_with_drive_id(self, mock_client):
        with patch.object(mock_client, 'get') as mock_get:
            mock_get.return_value = MockResponse(
                {"id": "drive1", "name": "Test Drive"})
            result = mock_client.drives("site1", "drive1")
            assert result["id"] == "drive1"
            mock_get.assert_called_once_with("/sites/site1/drives/drive1")

    def test_get_drive_items(self, mock_client):
        with patch.object(mock_client, 'get') as mock_get:
            mock_get.return_value = MockResponse(
                {"id": "item1", "name": "Test Item"})

            # Test with item_id only
            result = mock_client.get_drive_items(
                "site1", "drive1", item_id="item1")
            assert result["id"] == "item1"
            mock_get.assert_called_once_with(
                "/sites/site1/drives/drive1/items/item1")

            # Reset mock
            mock_get.reset_mock()

            # Test with path only
            result = mock_client.get_drive_items(
                "site1", "drive1", path="folder/file.txt")
            assert result["id"] == "item1"
            mock_get.assert_called_once_with(
                "/sites/site1/drives/drive1/root:/folder/file.txt")

    def test_get_drive_items_with_item_id_and_path(self, mock_client):
        with patch.object(mock_client, 'get') as mock_get:
            mock_get.return_value = MockResponse(
                {"id": "item1", "name": "Test Item"})
            result = mock_client.get_drive_items(
                "site1", "drive1", item_id="item1", path="subfolder")
            assert result["id"] == "item1"
            mock_get.assert_called_once_with(
                "/sites/site1/drives/drive1/items/item1:/subfolder")

    def test_get_drive_items_without_item_id_or_path(self, mock_client):
        with patch.object(mock_client, 'get') as mock_get:
            mock_get.return_value = MockResponse(
                {"id": "root", "name": "Root"})
            result = mock_client.get_drive_items("site1", "drive1")
            assert result["id"] == "root"
            mock_get.assert_called_once_with("/sites/site1/drives/drive1/root")

    def test_get_children(self, mock_client):
        with patch.object(mock_client, 'get') as mock_get:
            mock_get.return_value = MockResponse(
                {"value": [{"id": "item1", "name": "Test Item"}]})

            # Test with item_id
            result = mock_client.get_children("site1", "drive1", "folder1")
            assert result["value"][0]["id"] == "item1"
            mock_get.assert_called_once_with(
                "/sites/site1/drives/drive1/items/folder1/children")

            # Reset mock
            mock_get.reset_mock()

            # Test without item_id (root folder)
            result = mock_client.get_children("site1", "drive1")
            assert result["value"][0]["id"] == "item1"
            mock_get.assert_called_once_with(
                "/sites/site1/drives/drive1/root/children")

    def test_get_file_by_id(self, mock_client):
        with patch.object(mock_client, 'get') as mock_get:
            mock_get.return_value = MockResponse(
                {"id": "file1", "name": "test.txt", "file": {"hashes": {}}})
            result = mock_client.get_file_by_id("site1", "drive1", "file1")
            assert result["id"] == "file1"
            mock_get.assert_called_once_with(
                "/sites/site1/drives/drive1/items/file1")

    def test_refresh_token_if_needed(self, mock_client):
        with patch.object(mock_client, 'get_access_token') as mock_get_token:
            mock_get_token.return_value = "new-token"
            mock_client.refresh_token_if_needed()
            assert mock_client.access_token == "new-token"
            assert mock_client.headers == {'Authorization': 'Bearer new-token'}
            mock_get_token.assert_called_once()

    def test_build_url(self, mock_client):
        url = mock_client._build_url("/test/resource")
        expected_url = f"{mock_client.full_resource_url}/test/resource"
        assert url == expected_url

    def test_make_request_get(self, mock_client):
        with patch('requests.get') as mock_get:
            mock_get.return_value = MockResponse({"id": "item1"})
            response = mock_client._make_request('GET', '/test/resource')
            assert response.json() == {"id": "item1"}
            mock_get.assert_called_once_with(
                f"{mock_client.full_resource_url}/test/resource",
                headers=mock_client.headers,
                params=None
            )

    def test_make_request_post(self, mock_client):
        with patch('requests.post') as mock_post:
            mock_post.return_value = MockResponse({"id": "item1"})
            response = mock_client._make_request(
                'POST', '/test/resource', data='test-data')
            assert response.json() == {"id": "item1"}
            mock_post.assert_called_once_with(
                f"{mock_client.full_resource_url}/test/resource",
                headers=mock_client.headers,
                data='test-data',
                params=None
            )

    def test_make_request_put(self, mock_client):
        with patch('requests.put') as mock_put:
            mock_put.return_value = MockResponse({"id": "item1"})
            response = mock_client._make_request(
                'PUT', '/test/resource', data='test-data')
            assert response.json() == {"id": "item1"}
            mock_put.assert_called_once_with(
                f"{mock_client.full_resource_url}/test/resource",
                headers=mock_client.headers,
                data='test-data'
            )

    def test_make_request_unsupported_method(self, mock_client):
        try:
            mock_client._make_request('DELETE', '/test/resource')
            pytest.fail("Should have raised an error for unsupported method")
        except SharepointAPIError as e:
            assert "Unsupported HTTP method: DELETE" in str(e)

    def test_make_request_with_content_type(self, mock_client):
        with patch('requests.post') as mock_post:
            mock_post.return_value = MockResponse({"id": "item1"})
            response = mock_client._make_request(
                'POST', '/test/resource', content_type='application/json')
            assert response.json() == {"id": "item1"}
            expected_headers = mock_client.headers.copy()
            expected_headers['Content-Type'] = 'application/json'
            mock_post.assert_called_once_with(
                f"{mock_client.full_resource_url}/test/resource",
                headers=expected_headers,
                data=None,
                params=None
            )

    def test_make_request_http_error_not_401(self, mock_client):
        with patch('requests.get') as mock_get:
            # Create a proper HTTP error with response
            mock_response = MagicMock()
            mock_response.status_code = 404
            error = requests.HTTPError("404 Not Found")
            error.response = mock_response
            mock_response.raise_for_status.side_effect = error
            mock_get.return_value = mock_response

            with pytest.raises(ResourceNotFoundError):
                mock_client._make_request('GET', '/test/resource')

    def test_make_request_http_error_other(self, mock_client):
        with patch('requests.get') as mock_get:
            # Create a proper HTTP error with response
            mock_response = MagicMock()
            mock_response.status_code = 500
            error = requests.HTTPError("500 Server Error")
            error.response = mock_response
            mock_response.raise_for_status.side_effect = error
            mock_get.return_value = mock_response

            with pytest.raises(SharepointAPIError):
                mock_client._make_request('GET', '/test/resource')

    def test_make_request_connection_error(self, mock_client):
        with patch('requests.get') as mock_get:
            mock_get.side_effect = requests.RequestException(
                "Connection Error")

            with pytest.raises(ConnectionError):
                mock_client._make_request('GET', '/test/resource')

    def test_make_request_unexpected_error(self, mock_client):
        with patch('requests.get') as mock_get:
            mock_get.side_effect = Exception("Unexpected Error")

            with pytest.raises(SharepointAPIError):
                mock_client._make_request('GET', '/test/resource')

    def test_get_method(self, mock_client):
        with patch.object(mock_client, '_make_request') as mock_make_request:
            mock_make_request.return_value = MockResponse({"id": "item1"})
            response = mock_client.get('/test/resource')
            assert response.json() == {"id": "item1"}
            mock_make_request.assert_called_once_with(
                'GET', '/test/resource', params=None, headers=None)

    def test_post_method(self, mock_client):
        with patch.object(mock_client, '_make_request') as mock_make_request:
            mock_make_request.return_value = MockResponse({"id": "item1"})
            response = mock_client.post('/test/resource', data='test-data')
            assert response.json() == {"id": "item1"}
            mock_make_request.assert_called_once_with(
                'POST', '/test/resource', data='test-data', params=None, headers=None, content_type=None)

    def test_put_method(self, mock_client):
        with patch.object(mock_client, '_make_request') as mock_make_request:
            mock_make_request.return_value = MockResponse({"id": "item1"})
            response = mock_client.put('/test/resource', data='test-data')
            assert response.json() == {"id": "item1"}
            mock_make_request.assert_called_once_with(
                'PUT', '/test/resource', data='test-data', headers=None, content_type=None)

    def test_download_file(self, mock_client):
        with patch.object(mock_client, '_make_request') as mock_make_request, \
                patch('os.makedirs') as mock_makedirs, \
                patch('builtins.open', mock_open()) as mock_file:

            mock_make_request.return_value = MockResponse(
                {"content": "file content"},
                content=b"file content"
            )

            # Test with resource URL (starting with /)
            result = mock_client.download_file(
                "/download/url", "/tmp", "test.txt")
            assert result == "/tmp/test.txt"
            mock_make_request.assert_called_once_with('GET', '/download/url')
            mock_makedirs.assert_called_once_with("/tmp", exist_ok=True)
            mock_file.assert_called_once_with("/tmp/test.txt", 'wb')
            mock_file().write.assert_called_once_with(b"file content")

            # Reset mocks
            mock_make_request.reset_mock()
            mock_makedirs.reset_mock()
            mock_file.reset_mock()

            # Test with full URL (not starting with /)
            with patch('requests.get') as mock_get:
                mock_get.return_value = MockResponse(
                    {"content": "file content"},
                    content=b"file content"
                )
                result = mock_client.download_file(
                    "https://example.com/download", "/tmp", "test.txt")
                assert result == "/tmp/test.txt"
                mock_get.assert_called_once_with(
                    "https://example.com/download", headers=mock_client.headers)
                mock_makedirs.assert_called_once_with("/tmp", exist_ok=True)
                mock_file.assert_called_once_with("/tmp/test.txt", 'wb')
                mock_file().write.assert_called_once_with(b"file content")

    def test_download_file_os_error(self, mock_client):
        with patch.object(mock_client, '_make_request') as mock_make_request, \
                patch('os.makedirs') as mock_makedirs:

            mock_make_request.return_value = MockResponse(
                {"content": "file content"},
                content=b"file content"
            )
            mock_makedirs.side_effect = OSError("Permission denied")

            with pytest.raises(OSError):
                mock_client.download_file("/download/url", "/tmp", "test.txt")

    def test_download_file_unexpected_error(self, mock_client):
        with patch.object(mock_client, '_make_request') as mock_make_request:
            mock_make_request.side_effect = Exception("Unexpected error")

            with pytest.raises(SharepointAPIError):
                mock_client.download_file("/download/url", "/tmp", "test.txt")

    def test_upload_file(self, mock_client):
        with patch.object(mock_client, 'put') as mock_put:
            mock_put.return_value = MockResponse(
                {"id": "file1", "name": "test.txt"})

            data = b"file content"
            result = mock_client.upload_file(
                "site1", "drive1", "folder1", data, "test.txt")

            assert result == {"id": "file1", "name": "test.txt"}
            mock_put.assert_called_once_with(
                "/sites/site1/drives/drive1/items/folder1:/test.txt:/content",
                data=data,
                content_type="text/plain"
            )

    def test_upload_file_error(self, mock_client):
        with patch.object(mock_client, 'put') as mock_put:
            mock_put.side_effect = Exception("Upload error")

            data = b"file content"
            with pytest.raises(SharepointAPIError):
                mock_client.upload_file(
                    "site1", "drive1", "folder1", data, "test.txt")

    def test_download_folder_contents(self, mock_client):
        with patch.object(mock_client, 'get_children') as mock_get_children, \
                patch.object(mock_client, 'download_file') as mock_download_file, \
                patch('os.makedirs') as mock_makedirs:

            # Mock folder with 1 subfolder and 1 file
            mock_get_children.side_effect = [
                # First call - main folder
                {
                    "value": [
                        {
                            "id": "subfolder1",
                            "name": "subfolder",
                            "folder": {"childCount": 1}
                        },
                        {
                            "id": "file1",
                            "name": "test.txt",
                            "file": {"hashes": {}}
                        }
                    ]
                },
                # Second call - subfolder
                {
                    "value": [
                        {
                            "id": "subfile1",
                            "name": "subtest.txt",
                            "file": {"hashes": {}}
                        }
                    ]
                }
            ]

            mock_client.download_folder_contents(
                "site1", "drive1", "folder1", "/tmp/folder")

            # Should have made 2 calls to get_children
            assert mock_get_children.call_count == 2
            mock_get_children.assert_any_call("site1", "drive1", "folder1")
            mock_get_children.assert_any_call("site1", "drive1", "subfolder1")

            # Should have made 2 calls to download_file
            assert mock_download_file.call_count == 2
            mock_download_file.assert_any_call(
                "/sites/site1/drives/drive1/items/file1/content", "/tmp/folder", "test.txt")
            mock_download_file.assert_any_call(
                "/sites/site1/drives/drive1/items/subfile1/content", "/tmp/folder/subfolder", "subtest.txt")

            # Should have created the subfolder directory
            mock_makedirs.assert_called_once_with(
                "/tmp/folder/subfolder", exist_ok=True)

    def test_token_refresh(self, mock_client):
        # Setup for a 401 error then a successful retry
        with patch('requests.get') as mock_get:
            # First response (401 error)
            mock_first_response = MagicMock()
            mock_first_response.status_code = 401
            http_error = requests.HTTPError("401 Unauthorized")
            http_error.response = mock_first_response
            mock_first_response.raise_for_status.side_effect = http_error

            # Second response (success after token refresh)
            mock_second_response = MockResponse({"id": "item1"})

            # Set up the get method to return different responses on consecutive calls
            mock_get.side_effect = [mock_first_response, mock_second_response]

            # Call the method being tested
            with patch.object(mock_client, 'refresh_token_if_needed') as mock_refresh:
                response = mock_client._make_request('GET', '/test/resource')

                # Verify the refresh happened and request was retried
                mock_refresh.assert_called_once()
                assert mock_get.call_count == 2
                assert response.json() == {"id": "item1"}
