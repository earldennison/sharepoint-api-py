import pytest
import json
import os
from unittest.mock import patch, MagicMock, mock_open
import requests
from sharepoint_api.core.client import SharePointClient
from sharepoint_api.config import SharepointConfig
from sharepoint_api.data_models import (
    SharepointSite, SharepointSiteDrive, SharepointFolder, SharepointFile
)


@pytest.fixture
def mock_responses():
    """Fixture to provide common mock responses for tests"""

    # Authentication response
    auth_response = {
        "access_token": "mock-access-token",
        "token_type": "Bearer",
        "expires_in": 3600
    }

    # Site response
    site_response = {
        "value": [{
            "id": "site123",
            "name": "Test Site",
            "webUrl": "https://contoso.sharepoint.com/sites/testsite",
            "createdDateTime": "2023-01-01T00:00:00Z",
            "lastModifiedDateTime": "2023-01-02T00:00:00Z",
            "root": {},
            "siteCollection": {}
        }]
    }

    # Drives response
    drives_response = {
        "value": [{
            "id": "drive123",
            "name": "Documents",
            "description": "Document Library",
            "driveType": "documentLibrary",
            "createdDateTime": "2023-01-01T00:00:00Z",
            "lastModifiedDateTime": "2023-01-02T00:00:00Z",
            "webUrl": "https://contoso.sharepoint.com/sites/testsite/Documents",
            "createdBy": {"user": {"id": "user1", "displayName": "Test User", "email": "test@example.com"}},
            "lastModifiedBy": {"user": {"id": "user1", "displayName": "Test User", "email": "test@example.com"}},
            "owner": {"user": {"id": "user1", "displayName": "Test User", "email": "test@example.com"}},
            "quota": {"total": 1099511627776, "used": 1073741824}
        }]
    }

    # Root folder response
    root_folder_response = {
        "id": "root",
        "name": "root",
        "folder": {"childCount": 3},
        "createdDateTime": "2023-01-01T00:00:00Z",
        "lastModifiedDateTime": "2023-01-02T00:00:00Z",
        "webUrl": "https://contoso.sharepoint.com/sites/testsite/Documents",
        "parentReference": {"driveType": "documentLibrary", "driveId": "drive123", "id": "parent", "name": "Parent", "path": "/drive", "siteId": "site123"},
        "size": 0
    }

    # Folder content response
    folder_content_response = {
        "value": [
            {
                "id": "file1",
                "name": "test.txt",
                "file": {"hashes": {"quickXorHash": "hash123"}},
                "@microsoft.graph.downloadUrl": "https://contoso.sharepoint.com/sites/testsite/_api/download/test.txt",
                "createdDateTime": "2023-01-01T00:00:00Z",
                "lastModifiedDateTime": "2023-01-02T00:00:00Z",
                "webUrl": "https://contoso.sharepoint.com/sites/testsite/test.txt",
                "parentReference": {"driveType": "documentLibrary", "driveId": "drive123", "id": "root", "name": "Root", "path": "/drive/root", "siteId": "site123"},
                "size": 1024
            },
            {
                "id": "folder1",
                "name": "TestFolder",
                "folder": {"childCount": 2},
                "createdDateTime": "2023-01-01T00:00:00Z",
                "lastModifiedDateTime": "2023-01-02T00:00:00Z",
                "webUrl": "https://contoso.sharepoint.com/sites/testsite/TestFolder",
                "parentReference": {"driveType": "documentLibrary", "driveId": "drive123", "id": "root", "name": "Root", "path": "/drive/root", "siteId": "site123"},
                "size": 0
            }
        ]
    }

    # Subfolder content response
    subfolder_content_response = {
        "value": [
            {
                "id": "file2",
                "name": "subtest.txt",
                "file": {"hashes": {"quickXorHash": "hash456"}},
                "@microsoft.graph.downloadUrl": "https://contoso.sharepoint.com/sites/testsite/_api/download/subtest.txt",
                "createdDateTime": "2023-01-01T00:00:00Z",
                "lastModifiedDateTime": "2023-01-02T00:00:00Z",
                "webUrl": "https://contoso.sharepoint.com/sites/testsite/TestFolder/subtest.txt",
                "parentReference": {"driveType": "documentLibrary", "driveId": "drive123", "id": "folder1", "name": "TestFolder", "path": "/drive/root/folder1", "siteId": "site123"},
                "size": 512
            }
        ]
    }

    return {
        "auth": auth_response,
        "site": site_response,
        "drives": drives_response,
        "root_folder": root_folder_response,
        "folder_content": folder_content_response,
        "subfolder_content": subfolder_content_response
    }


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


class TestSharePointIntegration:

    def test_search_and_navigate_site(self, mock_responses):
        """Test the full flow of searching for a site and navigating its structure"""

        with patch('requests.post') as mock_post, \
                patch('requests.get') as mock_get, \
                patch.object(SharePointClient, '_make_request') as mock_request:

            # Setup mock responses for different API calls
            def mock_api_call(method, resource, **kwargs):
                if resource == "/sites" and kwargs.get('params', {}).get('search') == "Test Site":
                    return MockResponse(mock_responses["site"])
                elif resource == "/sites/site123/drives":
                    return MockResponse(mock_responses["drives"])
                elif resource == "/sites/site123/drives/drive123/root":
                    return MockResponse(mock_responses["root_folder"])
                elif resource == "/sites/site123/drives/drive123/items/root/children":
                    return MockResponse(mock_responses["folder_content"])
                elif resource == "/sites/site123/drives/drive123/items/folder1/children":
                    return MockResponse(mock_responses["subfolder_content"])
                return MockResponse({"error": "Unexpected request"}, 404)

            mock_request.side_effect = mock_api_call
            mock_post.return_value = MockResponse(mock_responses["auth"])

            # Create client and access SharePoint site
            client = SharePointClient(
                tenant_id="test-tenant",
                client_id="test-client",
                client_secret="test-secret",
                resource_url="https://graph.microsoft.com/",
                resource_url_version="v1.0"
            )

            # Get SharePoint site
            site = SharepointSite.from_name("Test Site", client)

            # Validate site properties
            assert site.id == "site123"
            assert site.name == "Test Site"

            # Get drives and validate
            drives = site.drives
            assert len(drives) == 1
            assert drives[0].id == "drive123"
            assert drives[0].name == "Documents"

            # Get root folder and validate content
            drive = drives[0]
            content = drive.content
            assert len(content) == 2

            # Find folder by name
            test_folder = None
            for item in content:
                if isinstance(item, SharepointFolder) and item.name == "TestFolder":
                    test_folder = item
                    break

            assert test_folder is not None

            # Get subfolder content
            subfolder_content = test_folder.content
            assert len(subfolder_content) == 1
            assert subfolder_content[0].name == "subtest.txt"

    def test_download_file(self, mock_responses):
        """Test downloading a file from SharePoint"""

        with patch('requests.post') as mock_post, \
                patch('requests.get') as mock_get, \
                patch.object(SharePointClient, '_make_request') as mock_request, \
                patch('os.makedirs') as mock_makedirs, \
                patch('builtins.open', mock_open()) as mock_file:

            # Setup mock responses
            def mock_api_call(method, resource, **kwargs):
                if resource == "/sites" and kwargs.get('params', {}).get('search') == "Test Site":
                    return MockResponse(mock_responses["site"])
                elif resource == "/sites/site123/drives":
                    return MockResponse(mock_responses["drives"])
                elif resource == "/sites/site123/drives/drive123/root":
                    return MockResponse(mock_responses["root_folder"])
                elif resource == "/sites/site123/drives/drive123/items/root/children":
                    return MockResponse(mock_responses["folder_content"])
                return MockResponse({"error": "Unexpected request"}, 404)

            mock_request.side_effect = mock_api_call
            mock_post.return_value = MockResponse(mock_responses["auth"])

            # Mock download request
            mock_get.return_value = MockResponse(
                {"content": "This is test file content"},
                content=b"This is test file content"
            )

            # Create client and access SharePoint site
            client = SharePointClient(
                tenant_id="test-tenant",
                client_id="test-client",
                client_secret="test-secret",
                resource_url="https://graph.microsoft.com/",
                resource_url_version="v1.0"
            )

            # Get site, drive, root folder and find test file
            site = SharepointSite.from_name("Test Site", client)
            drive = site.drives[0]
            content = drive.content

            test_file = None
            for item in content:
                if isinstance(item, SharepointFile) and item.name == "test.txt":
                    test_file = item
                    break

            assert test_file is not None

            # Download the file
            test_file.download("/tmp")

            # Verify file was downloaded correctly
            mock_get.assert_called_once_with(
                "https://contoso.sharepoint.com/sites/testsite/_api/download/test.txt"
            )
            mock_file.assert_called_once_with(
                os.path.join("/tmp", "test.txt"), 'wb')
            mock_file().write.assert_called_once_with(b"This is test file content")
