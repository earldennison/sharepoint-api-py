import pytest
import json
import os
from unittest.mock import patch, MagicMock, mock_open
import requests
from sharepoint_api.data_models import (
    RawFile, SharepointUserInfo, SharepointUser, SharepointParentReference,
    SharepointItem, SharepointFolderInfo, SharepointFileHashes, SharepointFile,
    SharepointFolder, SharepointSite, SharepointSiteDrive
)
from sharepoint_api.core.client import SharePointClient
from sharepoint_api.config import SharepointConfig


@pytest.fixture
def mock_client():
    client = MagicMock(spec=SharePointClient)
    client.get_access_token.return_value = "mock-token"
    client.headers = {"Authorization": "Bearer mock-token"}
    return client


@pytest.fixture
def sample_file_data():
    return {
        "createdBy": {"user": {"id": "user1", "displayName": "Test User", "email": "test@example.com"}},
        "createdDateTime": "2023-01-01T00:00:00Z",
        "eTag": "etag123",
        "id": "file1",
        "lastModifiedBy": {"user": {"id": "user1", "displayName": "Test User", "email": "test@example.com"}},
        "lastModifiedDateTime": "2023-01-02T00:00:00Z",
        "name": "test.txt",
        "webUrl": "https://example.com/test.txt",
        "parentReference": {"driveType": "documentLibrary", "driveId": "drive1", "id": "folder1", "name": "Folder", "path": "/drive/folder", "siteId": "site1"},
        "size": 1024,
        "file": {"hashes": {"quickXorHash": "hash123"}},
        "@microsoft.graph.downloadUrl": "https://example.com/download/test.txt"
    }


@pytest.fixture
def sample_folder_data():
    return {
        "createdBy": {"user": {"id": "user1", "displayName": "Test User", "email": "test@example.com"}},
        "createdDateTime": "2023-01-01T00:00:00Z",
        "eTag": "etag123",
        "id": "folder1",
        "lastModifiedBy": {"user": {"id": "user1", "displayName": "Test User", "email": "test@example.com"}},
        "lastModifiedDateTime": "2023-01-02T00:00:00Z",
        "name": "TestFolder",
        "webUrl": "https://example.com/folder",
        "parentReference": {"driveType": "documentLibrary", "driveId": "drive1", "id": "root", "name": "Root", "path": "/drive", "siteId": "site1"},
        "size": 0,
        "folder": {"childCount": 5}
    }


@pytest.fixture
def sample_site_data():
    return {
        "id": "site1",
        "createdDateTime": "2023-01-01T00:00:00Z",
        "lastModifiedDateTime": "2023-01-02T00:00:00Z",
        "name": "Test Site",
        "webUrl": "https://example.com/sites/testsite",
        "root": {},
        "siteCollection": {}
    }


@pytest.fixture
def sample_drive_data():
    return {
        "createdDateTime": "2023-01-01T00:00:00Z",
        "description": "Test Drive",
        "id": "drive1",
        "lastModifiedDateTime": "2023-01-02T00:00:00Z",
        "name": "Documents",
        "webUrl": "https://example.com/drives/documents",
        "driveType": "documentLibrary",
        "createdBy": {"user": {"id": "user1", "displayName": "Test User", "email": "test@example.com"}},
        "lastModifiedBy": {"user": {"id": "user1", "displayName": "Test User", "email": "test@example.com"}},
        "owner": {"user": {"id": "user1", "displayName": "Test User", "email": "test@example.com"}},
        "quota": {"total": 1099511627776, "used": 1073741824}
    }


class TestRawFile:
    def test_from_url(self):
        with patch('requests.get') as mock_get:
            mock_response = MagicMock()
            mock_response.content = b'test content'
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response

            raw_file = RawFile.from_url(
                "https://example.com/test.txt", "test.txt")

            assert raw_file.raw_data == b'test content'
            assert raw_file.file_name == "test.txt"
            assert raw_file.file_extension == "txt"

    def test_save(self):
        raw_file = RawFile(raw_data=b'test content',
                           file_name="test.txt", file_extension="txt")

        with patch('os.makedirs') as mock_makedirs, \
                patch('builtins.open', mock_open()) as mock_file:
            raw_file.save("/tmp/test.txt")

            mock_makedirs.assert_called_once_with(
                os.path.dirname("/tmp/test.txt"), exist_ok=True)
            mock_file.assert_called_once_with("/tmp/test.txt", 'wb')
            mock_file().write.assert_called_once_with(b'test content')


class TestSharepointModels:
    def test_sharepoint_file(self, sample_file_data):
        file = SharepointFile(**sample_file_data)

        assert file.id == "file1"
        assert file.name == "test.txt"
        assert file.download_url == "https://example.com/download/test.txt"
        assert file.size == 1024

    def test_sharepoint_folder(self, sample_folder_data, mock_client):
        folder = SharepointFolder(**sample_folder_data)
        folder._sharepoint_client = mock_client
        folder._sharepoint_site = MagicMock()
        folder._sharepoint_site.id = "site1"
        folder._sharepoint_drive = MagicMock()
        folder._sharepoint_drive.id = "drive1"

        # Mock the API response for folder contents
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "value": [
                {
                    "id": "file1",
                    "name": "test.txt",
                    "file": {"hashes": {}},
                    "@microsoft.graph.downloadUrl": "https://example.com/download/test.txt",
                    "createdDateTime": "2023-01-01T00:00:00Z",
                    "lastModifiedDateTime": "2023-01-02T00:00:00Z",
                    "webUrl": "https://example.com/test.txt",
                    "parentReference": {"driveType": "documentLibrary", "driveId": "drive1", "id": "folder1", "name": "Folder", "path": "/drive/folder", "siteId": "site1"},
                    "size": 1024
                }
            ]
        }
        mock_client.get.return_value = mock_response

        # Test the content property (which calls the API)
        content = folder.content
        assert len(content) == 1
        assert isinstance(content[0], SharepointFile)
        assert content[0].id == "file1"
        assert content[0].name == "test.txt"

        # Verify the API call was made correctly
        mock_client.get.assert_called_once_with(
            "/sites/site1/drives/drive1/items/folder1/children")

    def test_sharepoint_site(self, sample_site_data, sample_drive_data, mock_client):
        site = SharepointSite(**sample_site_data)
        site._sharepoint_client = mock_client

        # Mock the API response for site drives
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "value": [sample_drive_data]
        }
        mock_client.drives.return_value = mock_response.json()

        # Test the drives property (which calls the API)
        drives = site.drives
        assert len(drives) == 1
        assert isinstance(drives[0], SharepointSiteDrive)
        assert drives[0].id == "drive1"
        assert drives[0].name == "Documents"

        # Verify the API call was made correctly
        mock_client.drives.assert_called_once_with("site1")

    def test_sharepoint_drive(self, sample_drive_data, mock_client):
        drive = SharepointSiteDrive(**sample_drive_data)
        drive._sharepoint_client = mock_client
        drive._sharepoint_site = MagicMock()
        drive._sharepoint_site.id = "site1"

        # Mock the API response for root folder
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "id": "root",
            "name": "Root",
            "folder": {"childCount": 3},
            "createdDateTime": "2023-01-01T00:00:00Z",
            "lastModifiedDateTime": "2023-01-02T00:00:00Z",
            "webUrl": "https://example.com/root",
            "parentReference": {"driveType": "documentLibrary", "driveId": "drive1", "id": "parent", "name": "Parent", "path": "/drive", "siteId": "site1"},
            "size": 0
        }
        mock_client.get.return_value = mock_response

        # Get the root folder
        root_folder = drive.root_folder

        # Verify the root folder is properly created
        assert root_folder.id == "root"
        assert root_folder.name == "Root"
        assert root_folder.folder.child_count == 3

        # Verify the API call was made correctly
        mock_client.get.assert_called_once_with(
            f"/sites/{drive._sharepoint_site.id}/drives/{drive.id}/root")
