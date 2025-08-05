import pytest
from unittest.mock import patch, MagicMock
from httpx import Response, HTTPStatusError, Request

from sharepoint_api.core.client import SharePointClient, encode_share_link
from sharepoint_api.core.data_models import GraphSiteData, SiteMetaData, SharepointSiteDrive, SharepointSiteDrives, DriveItem, DriveFolder, DriveFile, FileInfo, FileSize
from sharepoint_api.core.errors import SharepointAPIError

# Dummy credentials and URLs for testing
TEST_CLIENT_ID = "test_client_id"
TEST_CLIENT_SECRET = "test_client_secret"
TEST_RESOURCE_URL = "https://graph.microsoft.com/"
TEST_RESOURCE_URL_VERSION = "v1.0"
TEST_TENANT_ID = "test_tenant_id"
TEST_SITE_ID = "test_site_id_123"
TEST_DRIVE_ID = "test_drive_id_456"
TEST_ITEM_ID = "test_item_id_789"

@pytest.fixture
def mock_oauth_client():
    with patch('sharepoint_api.core.client.OAuth2Client') as mock_oauth:
        mock_oauth_instance = mock_oauth.return_value
        mock_oauth_instance.fetch_token.return_value = {
            "access_token": "test_access_token",
            "token_type": "Bearer",
            "expires_in": 3600
        }
        yield mock_oauth_instance

@pytest.fixture
def client(mock_oauth_client):
    """Pytest fixture to create a SharePointClient with mocked authentication."""
    return SharePointClient(
        client_id=TEST_CLIENT_ID,
        client_secret=TEST_CLIENT_SECRET,
        resource_url=TEST_RESOURCE_URL,
        resource_url_version=TEST_RESOURCE_URL_VERSION,
        tenant_id=TEST_TENANT_ID
    )

def test_encode_share_link():
    share_url = "https://tenant.sharepoint.com/sites/MySite/Shared%20Documents/MyFile.docx"
    expected_encoded_url = "u!aHR0cHM6Ly90ZW5hbnQuc2hhcmVwb2ludC5jb20vc2l0ZXMvTXlTaXRlL1NoYXJlZCUyMERvY3VtZW50cy9NeUZpbGUuZG9jeA"
    assert encode_share_link(share_url) == expected_encoded_url

    share_url_with_equals = "https://example.com/somepath?query=param==" # Simulating a base64 that might have padding
    # Actual base64 of above: aHR0cHM6Ly9leGFtcGxlLmNvbS9zb21lcGF0aD9xdWVyeT1wYXJhbT09
    # After stripping '=' : aHR0cHM6Ly9leGFtcGxlLmNvbS9zb21lcGF0aD9xdWVyeT1wYXJhbT0
    # Prepending u!
    expected_encoded_url_eq = "u!aHR0cHM6Ly9leGFtcGxlLmNvbS9zb21lcGF0aD9xdWVyeT1wYXJhbT0"
    assert encode_share_link(share_url_with_equals) == expected_encoded_url_eq


def test_get_sites_success(client):
    """Test get_sites successfully returns SiteMetaData."""
    mock_response_data = {
        "@odata.context": "sites_context",
        "value": [
            {
                "createdDateTime": "2023-01-01T00:00:00Z",
                "displayName": "Test Site 1",
                "id": "site1",
                "lastModifiedDateTime": "2023-01-02T00:00:00Z",
                "name": "test-site-1",
                "webUrl": "https://tenant.sharepoint.com/sites/test-site-1"
            }
        ]
    }
    with patch.object(client, 'get', autospec=True) as mock_get:
        mock_get.return_value = MagicMock(spec=Response)
        mock_get.return_value.json.return_value = mock_response_data
        mock_get.return_value.status_code = 200
        mock_get.return_value.raise_for_status = MagicMock()

        sites_metadata = client.get_sites()

        mock_get.assert_called_once_with('/sites', params={})
        assert isinstance(sites_metadata, SiteMetaData)
        assert len(sites_metadata.value) == 1
        assert sites_metadata.value[0].displayName == "Test Site 1"

def test_get_sites_with_search(client):
    """Test get_sites with a search query."""
    search_query = "ProjectX"
    mock_response_data = {
        "@odata.context": "sites_context_search",
        "value": [
            {
                "createdDateTime": "2023-02-01T00:00:00Z",
                "displayName": "ProjectX Site",
                "id": "siteX",
                "lastModifiedDateTime": "2023-02-02T00:00:00Z",
                "name": "projectx-site",
                "webUrl": "https://tenant.sharepoint.com/sites/projectx-site"
            }
        ]
    }
    with patch.object(client, 'get', autospec=True) as mock_get:
        mock_get.return_value = MagicMock(spec=Response)
        mock_get.return_value.json.return_value = mock_response_data
        mock_get.return_value.status_code = 200
        mock_get.return_value.raise_for_status = MagicMock()
        
        sites_metadata = client.get_sites(search=search_query)

        mock_get.assert_called_once_with('/sites', params={'search': search_query})
        assert isinstance(sites_metadata, SiteMetaData)
        assert sites_metadata.value[0].name == "projectx-site"

def test_get_sites_http_error(client):
    """Test get_sites raises SharepointAPIError on HTTP error."""
    with patch.object(client, 'get', autospec=True) as mock_get:
        # Configure the mock to raise HTTPStatusError, similar to how httpx.Response.raise_for_status() would
        mock_response = MagicMock(spec=Response)
        mock_response.status_code = 404
        mock_response.text = "Not Found"
        mock_response.request = Request(method="GET", url="/sites") # Add request object
        
        mock_get.return_value = mock_response # Return the mock response
        mock_get.return_value.raise_for_status.side_effect = HTTPStatusError(
            "Not Found", request=mock_response.request, response=mock_response
        )
        
        with pytest.raises(HTTPStatusError): # Expecting HTTPStatusError now as per client changes
            client.get_sites()
        mock_get.assert_called_once_with('/sites', params={})

# --- Tests for get_site ---
def test_get_site_by_id_success(client):
    mock_site_data = {
        "createdDateTime": "2023-01-01T00:00:00Z", "displayName": "Site From ID", "id": TEST_SITE_ID,
        "lastModifiedDateTime": "2023-01-02T00:00:00Z", "name": "site-from-id",
        "webUrl": f"https://tenant.sharepoint.com/sites/site-from-id"
    }
    with patch.object(client, 'get', autospec=True) as mock_get:
        mock_get.return_value = MagicMock(spec=Response)
        mock_get.return_value.json.return_value = mock_site_data
        mock_get.return_value.status_code = 200
        mock_get.return_value.raise_for_status = MagicMock()

        site = client.get_site(site_id=TEST_SITE_ID)

        mock_get.assert_called_once_with(f"/sites/{TEST_SITE_ID}")
        assert isinstance(site, GraphSiteData)
        assert site.id == TEST_SITE_ID
        assert site.displayName == "Site From ID"
        assert client.current_site == site

def test_get_site_by_id_not_found(client):
    with patch.object(client, 'get', autospec=True) as mock_get:
        mock_response = MagicMock(spec=Response)
        mock_response.status_code = 404
        mock_response.text = "Site Not Found"
        mock_response.request = Request(method="GET", url=f"/sites/{TEST_SITE_ID}")
        mock_get.return_value = mock_response
        mock_get.return_value.raise_for_status.side_effect = HTTPStatusError(
            "Site Not Found", request=mock_response.request, response=mock_response
        )

        site = client.get_site(site_id=TEST_SITE_ID)
        
        mock_get.assert_called_once_with(f"/sites/{TEST_SITE_ID}")
        assert site is None

def test_get_site_by_name_success(client):
    site_name_to_find = "Unique Site Name"
    mock_sites_response = {
        "@odata.context": "sites_context",
        "value": [
            {"createdDateTime": "2023-01-01T00:00:00Z", "displayName": "Other Site", "id": "other1",
             "lastModifiedDateTime": "2023-01-01T00:00:00Z", "name": "other-site", "webUrl": "..."},
            {"createdDateTime": "2023-02-01T00:00:00Z", "displayName": site_name_to_find, "id": "unique1",
             "lastModifiedDateTime": "2023-02-01T00:00:00Z", "name": site_name_to_find, "webUrl": "..."}
        ]
    }
    with patch.object(client, 'get', autospec=True) as mock_internal_get: # Mocks the client's own .get() method
        # This mock_internal_get will be used by get_sites() when it's called
        mock_internal_get.return_value = MagicMock(spec=Response)
        mock_internal_get.return_value.json.return_value = mock_sites_response
        mock_internal_get.return_value.status_code = 200
        mock_internal_get.return_value.raise_for_status = MagicMock()
        
        found_site = client.get_site(site_name=site_name_to_find)

        mock_internal_get.assert_called_once_with('/sites', params={}) # get_sites was called
        assert found_site is not None
        assert found_site.name == site_name_to_find
        assert client.current_site == found_site

def test_get_site_by_name_not_found(client):
    site_name_to_find = "NonExistent Site"
    mock_sites_response = {
        "@odata.context": "sites_context", "value": [] # Empty list, site not found
    }
    with patch.object(client, 'get', autospec=True) as mock_internal_get:
        mock_internal_get.return_value = MagicMock(spec=Response)
        mock_internal_get.return_value.json.return_value = mock_sites_response
        mock_internal_get.return_value.status_code = 200
        mock_internal_get.return_value.raise_for_status = MagicMock()

        found_site = client.get_site(site_name=site_name_to_find)
        
        assert found_site is None
        # current_site should not be updated if no site is found
        # Depending on implementation, you might want to assert client.current_site remains unchanged or becomes None

def test_get_site_by_web_url_direct_hit_success(client):
    web_url = "https://tenant.sharepoint.com/sites/MyWebUrlSite"
    mock_site_data = {
        "createdDateTime": "2023-03-01T00:00:00Z", "displayName": "MyWebUrlSite", "id": "weburlsite1",
        "lastModifiedDateTime": "2023-03-01T00:00:00Z", "name": "myweburlsite", "webUrl": web_url
    }
    # Mock SharePointUrl.from_weburl if its internal logic is complex or makes external calls
    # For this test, assume it correctly parses the URL.
    expected_relative_url = "tenant.sharepoint.com:/sites/MyWebUrlSite" # Example, ensure this matches SharePointUrl logic

    with patch.object(client, 'get', autospec=True) as mock_get:
        mock_get.return_value = MagicMock(spec=Response)
        mock_get.return_value.json.return_value = mock_site_data
        mock_get.return_value.status_code = 200
        mock_get.return_value.raise_for_status = MagicMock()

        with patch('sharepoint_api.core.client.SharePointUrl') as mock_sp_url:
            mock_sp_url.from_weburl.return_value.relative_server_url = expected_relative_url
            
            site = client.get_site(web_url=web_url)

            mock_sp_url.from_weburl.assert_called_once_with(web_url)
            mock_get.assert_called_once_with(f"/sites/{expected_relative_url}")
            assert site is not None
            assert site.webUrl == web_url
            assert client.current_site == site

def test_get_site_by_web_url_fallback_to_search_success(client):
    web_url = "https://tenant.sharepoint.com/sites/SearchFallbackSite"
    # First call to /sites/{relative_url} will fail (direct lookup)
    # Second call to /sites (for search) will succeed
    mock_site_data_search = {
        "createdDateTime": "2023-04-01T00:00:00Z", "displayName": "SearchFallbackSite", "id": "searchfallback1",
        "lastModifiedDateTime": "2023-04-01T00:00:00Z", "name": "searchfallbacksite", "webUrl": web_url
    }
    mock_sites_list_response = {"@odata.context": "sites_context", "value": [mock_site_data_search]}
    
    expected_relative_url = "tenant.sharepoint.com:/sites/SearchFallbackSite"

    with patch.object(client, 'get', autospec=True) as mock_get:
        # Simulate failure for direct lookup, success for search lookup
        direct_lookup_response = MagicMock(spec=Response)
        direct_lookup_response.status_code = 404
        direct_lookup_response.text = "Not Found Direct"
        direct_lookup_response.request = Request(method="GET", url=f"/sites/{expected_relative_url}")
        direct_lookup_response.raise_for_status.side_effect = HTTPStatusError(
            "Not Found Direct", request=direct_lookup_response.request, response=direct_lookup_response
        )

        search_lookup_response = MagicMock(spec=Response)
        search_lookup_response.json.return_value = mock_sites_list_response
        search_lookup_response.status_code = 200
        search_lookup_response.raise_for_status = MagicMock()

        # Make mock_get return different values on subsequent calls
        mock_get.side_effect = [direct_lookup_response, search_lookup_response]

        with patch('sharepoint_api.core.client.SharePointUrl') as mock_sp_url:
            mock_sp_url.from_weburl.return_value.relative_server_url = expected_relative_url

            site = client.get_site(web_url=web_url)

            assert mock_sp_url.from_weburl.call_count == 1 # Called for direct, then SiteMetaData.search uses it
            assert mock_get.call_count == 2
            mock_get.assert_any_call(f"/sites/{expected_relative_url}") # Direct lookup attempt
            mock_get.assert_any_call('/sites', params={})         # Search lookup attempt (get_sites)
            
            assert site is not None
            assert site.webUrl == web_url
            assert client.current_site == site

def test_get_site_no_params(client):
    site = client.get_site()
    assert site is None

# --- Tests for get_drive ---

DRIVE_RESPONSE_A = {
    "createdDateTime": "2023-01-01T10:00:00Z", "description": "Primary Drive", "id": "driveA123",
    "lastModifiedDateTime": "2023-01-10T10:00:00Z", "name": "Documents",
    "webUrl": "https://tenant.sharepoint.com/sites/MySite/Shared%20Documents", "driveType": "documentLibrary",
    "quota": {"total": 1000000, "used": 200000}
}
DRIVE_RESPONSE_B = {
    "createdDateTime": "2023-02-01T10:00:00Z", "description": "Archive Drive", "id": "driveB456",
    "lastModifiedDateTime": "2023-02-10T10:00:00Z", "name": "Archive",
    "webUrl": "https://tenant.sharepoint.com/sites/MySite/Archive%20Docs", "driveType": "documentLibrary",
    "quota": {"total": 5000000, "used": 1000000}
}

def test_get_drive_by_id_success(client):
    client.current_site = GraphSiteData(id=TEST_SITE_ID, displayName="Test Site", name="test-site", webUrl="...", createdDateTime="2023-01-01T00:00:00Z")
    
    with patch.object(client, 'get', autospec=True) as mock_get:
        mock_get.return_value = MagicMock(spec=Response)
        mock_get.return_value.json.return_value = DRIVE_RESPONSE_A
        mock_get.return_value.status_code = 200
        mock_get.return_value.raise_for_status = MagicMock()

        drive = client.get_drive(drive_id="driveA123")

        mock_get.assert_called_once_with(f"/sites/{TEST_SITE_ID}/drives/driveA123")
        assert isinstance(drive, SharepointSiteDrive)
        assert drive.id == "driveA123"
        assert drive.name == "Documents"
        assert client.current_drive == drive

def test_get_drive_by_id_with_site_id_param(client):
    # No client.current_site set
    with patch.object(client, 'get', autospec=True) as mock_get:
        mock_get.return_value = MagicMock(spec=Response)
        mock_get.return_value.json.return_value = DRIVE_RESPONSE_A
        mock_get.return_value.status_code = 200
        mock_get.return_value.raise_for_status = MagicMock()

        drive = client.get_drive(site_id="customSiteId", drive_id="driveA123")

        mock_get.assert_called_once_with(f"/sites/customSiteId/drives/driveA123")
        assert isinstance(drive, SharepointSiteDrive)
        assert drive.id == "driveA123"

def test_get_drive_by_id_not_found(client):
    client.current_site = GraphSiteData(id=TEST_SITE_ID, displayName="Test Site", name="test-site", webUrl="...", createdDateTime="2023-01-01T00:00:00Z")
    with patch.object(client, 'get', autospec=True) as mock_get:
        mock_response = MagicMock(spec=Response)
        mock_response.status_code = 404
        mock_response.text = "Drive Not Found"
        mock_response.request = Request(method="GET", url=f"/sites/{TEST_SITE_ID}/drives/nonexistentDrive")
        mock_get.return_value = mock_response
        mock_get.return_value.raise_for_status.side_effect = HTTPStatusError(
            "Drive Not Found", request=mock_response.request, response=mock_response
        )
        
        drive = client.get_drive(drive_id="nonexistentDrive")
        
        assert drive is None

def test_get_drive_no_site_id_context(client):
    # client.current_site is None by default in fixture if not set
    drive = client.get_drive(drive_id="someDrive")
    assert drive is None # Should return None as per refined logic

def test_get_all_drives_for_site_success(client):
    client.current_site = GraphSiteData(id=TEST_SITE_ID, displayName="Test Site", name="test-site", webUrl="...", createdDateTime="2023-01-01T00:00:00Z")
    mock_drives_list_response = {"value": [DRIVE_RESPONSE_A, DRIVE_RESPONSE_B]}

    with patch.object(client, 'get', autospec=True) as mock_get:
        mock_get.return_value = MagicMock(spec=Response)
        mock_get.return_value.json.return_value = mock_drives_list_response
        mock_get.return_value.status_code = 200
        mock_get.return_value.raise_for_status = MagicMock()

        drives = client.get_drive() # No drive_id or drive_name, should get all

        mock_get.assert_called_once_with(f"/sites/{TEST_SITE_ID}/drives")
        assert isinstance(drives, SharepointSiteDrives)
        assert len(drives.root) == 2
        assert drives.root[0].name == "Documents"
        assert drives.root[1].name == "Archive"
        # current_drive should not be set when multiple drives are returned
        assert client.current_drive is None 

def test_get_drive_by_name_success(client):
    client.current_site = GraphSiteData(id=TEST_SITE_ID, displayName="Test Site", name="test-site", webUrl="...", createdDateTime="2023-01-01T00:00:00Z")
    mock_drives_list_response = {"value": [DRIVE_RESPONSE_A, DRIVE_RESPONSE_B]}
    drive_name_to_find = "Archive"

    with patch.object(client, 'get', autospec=True) as mock_get:
        # This mock_get is for the call to /sites/{site_id}/drives
        mock_get.return_value = MagicMock(spec=Response)
        mock_get.return_value.json.return_value = mock_drives_list_response
        mock_get.return_value.status_code = 200
        mock_get.return_value.raise_for_status = MagicMock()

        drive = client.get_drive(drive_name=drive_name_to_find)

        mock_get.assert_called_once_with(f"/sites/{TEST_SITE_ID}/drives")
        assert isinstance(drive, SharepointSiteDrive)
        assert drive.name == drive_name_to_find
        assert drive.id == "driveB456"
        assert client.current_drive == drive

def test_get_drive_by_name_not_found(client):
    client.current_site = GraphSiteData(id=TEST_SITE_ID, displayName="Test Site", name="test-site", webUrl="...", createdDateTime="2023-01-01T00:00:00Z")
    mock_drives_list_response = {"value": [DRIVE_RESPONSE_A]} # "Archive" is not here
    drive_name_to_find = "NonExistentDriveName"

    with patch.object(client, 'get', autospec=True) as mock_get:
        mock_get.return_value = MagicMock(spec=Response)
        mock_get.return_value.json.return_value = mock_drives_list_response
        mock_get.return_value.status_code = 200
        mock_get.return_value.raise_for_status = MagicMock()

        drive = client.get_drive(drive_name=drive_name_to_find)
        assert drive is None
        # client.current_drive might be None or last valid one depending on exact path through logic

# --- Tests for get_drive_items ---
ITEM_FILE_A = {
    "@odata.context": "file_context", "@microsoft.graph.downloadUrl": "https://download.example.com/fileA",
    "createdBy": {"user": {"displayName": "User A"}}, "createdDateTime": "2023-05-01T10:00:00Z",
    "id": "fileA123", "lastModifiedBy": {"user": {"displayName": "User B"}}, "lastModifiedDateTime": "2023-05-01T11:00:00Z",
    "name": "Report.docx", "webUrl": "https://tenant.sharepoint.com/sites/MySite/Shared%20Documents/Report.docx",
    "size": 10240, "file": {"mimeType": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}
}
ITEM_FOLDER_B = {
    "@odata.context": "folder_context",
    "createdBy": {"user": {"displayName": "User C"}}, "createdDateTime": "2023-05-02T10:00:00Z",
    "id": "folderB456", "lastModifiedBy": {"user": {"displayName": "User D"}}, "lastModifiedDateTime": "2023-05-02T11:00:00Z",
    "name": "Monthly Reports", "webUrl": "https://tenant.sharepoint.com/sites/MySite/Shared%20Documents/Monthly%20Reports",
    "size": 51200, "folder": {"childCount": 2}, "parentReference": {"driveId": TEST_DRIVE_ID, "id": "root"}
}
ITEM_FILE_C_IN_FOLDER_B = { # Child of Folder B
    "@odata.context": "file_context_child", "@microsoft.graph.downloadUrl": "https://download.example.com/fileC",
    "id": "fileC789", "name": "January.pdf", "size": 2048, "file": {"mimeType": "application/pdf"},
    "parentReference": {"driveId": TEST_DRIVE_ID, "id": "folderB456"}
}

def test_get_drive_item_by_id_file_success(client):
    client.current_site = GraphSiteData(id=TEST_SITE_ID, displayName="Test Site", name="test-site", webUrl="...", createdDateTime="2023-01-01T00:00:00Z")
    client.current_drive = SharepointSiteDrive(**DRIVE_RESPONSE_A) # Set current_drive
    
    with patch.object(client, 'get', autospec=True) as mock_get:
        mock_get.return_value = MagicMock(spec=Response)
        mock_get.return_value.json.return_value = ITEM_FILE_A
        mock_get.return_value.status_code = 200
        mock_get.return_value.raise_for_status = MagicMock()

        item = client.get_drive_items(item_id="fileA123")

        mock_get.assert_called_once_with(f"/sites/{TEST_SITE_ID}/drives/{DRIVE_RESPONSE_A['id']}/items/fileA123")
        assert isinstance(item, DriveFile)
        assert item.id == "fileA123"
        assert item.name == "Report.docx"

def test_get_drive_item_by_path_success(client):
    client.current_site = GraphSiteData(id=TEST_SITE_ID, displayName="Test Site", name="test-site", webUrl="...", createdDateTime="2023-01-01T00:00:00Z")
    client.current_drive = SharepointSiteDrive(**DRIVE_RESPONSE_A)
    item_path = "MyFolder/MyFile.txt"
    
    with patch.object(client, 'get', autospec=True) as mock_get:
        mock_get.return_value = MagicMock(spec=Response)
        # Assume the path resolves to ITEM_FILE_A for simplicity
        mock_get.return_value.json.return_value = ITEM_FILE_A 
        mock_get.return_value.status_code = 200
        mock_get.return_value.raise_for_status = MagicMock()

        item = client.get_drive_items(path=item_path)

        mock_get.assert_called_once_with(f"/sites/{TEST_SITE_ID}/drives/{DRIVE_RESPONSE_A['id']}/root:/{item_path.lstrip('/')}")
        assert isinstance(item, DriveFile)
        assert item.name == "Report.docx" # Based on ITEM_FILE_A

def test_get_drive_item_folder_with_children_success(client):
    client.current_site = GraphSiteData(id=TEST_SITE_ID, displayName="Test Site", name="test-site", webUrl="...", createdDateTime="2023-01-01T00:00:00Z")
    client.current_drive = SharepointSiteDrive(**DRIVE_RESPONSE_A) # id is 'driveA123'
    
    # Mock response for the folder itself
    mock_folder_response = MagicMock(spec=Response)
    mock_folder_response.json.return_value = ITEM_FOLDER_B # folderB456
    mock_folder_response.status_code = 200
    mock_folder_response.raise_for_status = MagicMock()

    # Mock response for the children of the folder
    mock_children_response = MagicMock(spec=Response)
    mock_children_response.json.return_value = {"value": [ITEM_FILE_C_IN_FOLDER_B]}
    mock_children_response.status_code = 200
    mock_children_response.raise_for_status = MagicMock()

    with patch.object(client, 'get', autospec=True) as mock_get:
        mock_get.side_effect = [mock_folder_response, mock_children_response]

        folder_item = client.get_drive_items(item_id="folderB456")

        assert mock_get.call_count == 2
        mock_get.assert_any_call(f"/sites/{TEST_SITE_ID}/drives/{DRIVE_RESPONSE_A['id']}/items/folderB456")
        mock_get.assert_any_call(f"/sites/{TEST_SITE_ID}/drives/{DRIVE_RESPONSE_A['id']}/items/folderB456/children")
        
        assert isinstance(folder_item, DriveFolder)
        assert folder_item.id == "folderB456"
        assert folder_item.name == "Monthly Reports"
        assert len(folder_item.children) == 1
        assert isinstance(folder_item.children[0], DriveFile)
        assert folder_item.children[0].name == "January.pdf"

def test_get_drive_items_no_ids_or_path_gets_root(client):
    client.current_site = GraphSiteData(id=TEST_SITE_ID, displayName="Test Site", name="test-site", webUrl="...", createdDateTime="2023-01-01T00:00:00Z")
    client.current_drive = SharepointSiteDrive(**DRIVE_RESPONSE_A) # id is 'driveA123'
    
    # Mock response for the root item (typically a folder)
    mock_root_folder_data = {**ITEM_FOLDER_B, "name": "root", "id": "rootFolderId"} 
    mock_root_children_data = {"value": [ITEM_FILE_A]}


    with patch.object(client, 'get', autospec=True) as mock_get:
        root_response = MagicMock(spec=Response)
        root_response.json.return_value = mock_root_folder_data
        root_response.status_code = 200
        root_response.raise_for_status = MagicMock()

        children_response = MagicMock(spec=Response)
        children_response.json.return_value = mock_root_children_data
        children_response.status_code = 200
        children_response.raise_for_status = MagicMock()
        
        mock_get.side_effect = [root_response, children_response]


        root_item = client.get_drive_items() # No item_id, no path

        assert mock_get.call_count == 2
        mock_get.assert_any_call(f"/sites/{TEST_SITE_ID}/drives/{DRIVE_RESPONSE_A['id']}/root")
        mock_get.assert_any_call(f"/sites/{TEST_SITE_ID}/drives/{DRIVE_RESPONSE_A['id']}/items/rootFolderId/children")

        assert isinstance(root_item, DriveFolder)
        assert root_item.name == "root"
        assert len(root_item.children) == 1
        assert root_item.children[0].name == "Report.docx"

def test_get_drive_items_not_found(client):
    client.current_site = GraphSiteData(id=TEST_SITE_ID, displayName="Test Site", name="test-site", webUrl="...", createdDateTime="2023-01-01T00:00:00Z")
    client.current_drive = SharepointSiteDrive(**DRIVE_RESPONSE_A)

    with patch.object(client, 'get', autospec=True) as mock_get:
        mock_response = MagicMock(spec=Response)
        mock_response.status_code = 404
        mock_response.text = "Item Not Found"
        req_url = f"/sites/{TEST_SITE_ID}/drives/{DRIVE_RESPONSE_A['id']}/items/nonexistentitem"
        mock_response.request = Request(method="GET", url=req_url)
        mock_get.return_value = mock_response
        mock_get.return_value.raise_for_status.side_effect = HTTPStatusError(
            "Item Not Found", request=mock_response.request, response=mock_response
        )
        
        item = client.get_drive_items(item_id="nonexistentitem")
        assert item is None

def test_get_drive_items_no_site_or_drive_context(client):
    # client.current_site and client.current_drive are None
    item = client.get_drive_items(item_id="someitem")
    assert item is None # Should return None if site/drive can't be resolved


# --- Tests for path method ---
@patch('sharepoint_api.core.client.SharePointClient.get_drive_items')
@patch('sharepoint_api.core.client.SharePointClient.get_drive')
@patch('sharepoint_api.core.client.SharePointClient.get_site')
@patch('sharepoint_api.core.client.SharePointClient.get_shares')
@patch('sharepoint_api.core.client.SharePointUrl')
def test_path_direct_file_link(mock_sp_url_class, mock_get_shares, mock_get_site, mock_get_drive, mock_get_drive_items, client):
    test_share_url = "https://tenant.sharepoint.com/:x:/s/SiteName/FileIdString"
    
    mock_sp_url_instance = mock_sp_url_class.from_weburl.return_value
    mock_sp_url_instance.is_direct_file = True
    mock_sp_url_instance.full_url = test_share_url

    mock_get_shares.return_value = ITEM_FILE_A # Simulate get_shares returns file data

    item = client.path(test_share_url)

    mock_sp_url_class.from_weburl.assert_called_once_with(test_share_url)
    mock_get_shares.assert_called_once_with(test_share_url)
    assert isinstance(item, DriveFile)
    assert item.id == ITEM_FILE_A['id']
    mock_get_site.assert_not_called()
    mock_get_drive.assert_not_called()
    mock_get_drive_items.assert_not_called()

@patch('sharepoint_api.core.client.SharePointClient.get_drive_items')
@patch('sharepoint_api.core.client.SharePointClient.get_drive')
@patch('sharepoint_api.core.client.SharePointClient.get_site')
@patch('sharepoint_api.core.client.SharePointClient.get_shares')
@patch('sharepoint_api.core.client.SharePointUrl')
def test_path_regular_folder_path(mock_sp_url_class, mock_get_shares, mock_get_site, mock_get_drive, mock_get_drive_items, client):
    test_folder_url = "https://tenant.sharepoint.com/sites/MySite/Shared%20Documents/Monthly%20Reports"

    mock_sp_url_instance = mock_sp_url_class.from_weburl.return_value
    mock_sp_url_instance.is_direct_file = False
    mock_sp_url_instance.drive.name = "Shared Documents" # Extracted drive name by SharePointUrl
    mock_sp_url_instance.drive.path = "Monthly Reports" # Extracted item path by SharePointUrl
    
    # Mock chain of calls
    mock_site = GraphSiteData(id=TEST_SITE_ID, name="MySite", displayName="My Site", webUrl="...", createdDateTime="...")
    mock_get_site.return_value = mock_site
    
    mock_drive = SharepointSiteDrive(**DRIVE_RESPONSE_A) # id "driveA123", name "Documents"
    # Let's assume drive name from URL is "Shared Documents" which maps to this drive
    mock_get_drive.return_value = mock_drive 
    
    mock_get_drive_items.return_value = DriveFolder(**ITEM_FOLDER_B) # Returns the folder item

    item = client.path(test_folder_url)

    mock_sp_url_class.from_weburl.assert_called_once_with(test_folder_url)
    mock_get_shares.assert_not_called()
    mock_get_site.assert_called_once_with(web_url=test_folder_url)
    mock_get_drive.assert_called_once_with(site_id=TEST_SITE_ID, drive_name="Shared Documents")
    mock_get_drive_items.assert_called_once_with(site_id=TEST_SITE_ID, drive_id=DRIVE_RESPONSE_A['id'], path="Monthly Reports")

    assert isinstance(item, DriveFolder)
    assert item.id == ITEM_FOLDER_B['id']

@patch('sharepoint_api.core.client.SharePointClient.get_site', return_value=None)
@patch('sharepoint_api.core.client.SharePointUrl')
def test_path_site_not_found(mock_sp_url_class, mock_get_site, client):
    test_url = "https://tenant.sharepoint.com/sites/NonExistentSite/Docs"
    mock_sp_url_instance = mock_sp_url_class.from_weburl.return_value
    mock_sp_url_instance.is_direct_file = False
    
    item = client.path(test_url)
    assert item is None
    mock_get_site.assert_called_once_with(web_url=test_url)

@patch('sharepoint_api.core.client.SharePointClient.get_drive', return_value=None) # Drive not found
@patch('sharepoint_api.core.client.SharePointClient.get_site')
@patch('sharepoint_api.core.client.SharePointUrl')
def test_path_drive_not_found(mock_sp_url_class, mock_get_site, mock_get_drive, client):
    test_url = "https://tenant.sharepoint.com/sites/MySite/NonExistentDrive/Folder"
    
    mock_sp_url_instance = mock_sp_url_class.from_weburl.return_value
    mock_sp_url_instance.is_direct_file = False
    mock_sp_url_instance.drive.name = "NonExistentDrive"
    
    mock_site = GraphSiteData(id=TEST_SITE_ID, name="MySite", displayName="My Site", webUrl="...", createdDateTime="...")
    mock_get_site.return_value = mock_site
    
    item = client.path(test_url)
    assert item is None
    mock_get_drive.assert_called_once_with(site_id=TEST_SITE_ID, drive_name="NonExistentDrive")

# --- Tests for upload_file ---
def test_upload_file_success(client):
    file_data = b"Hello SharePoint"
    file_name = "hello.txt"
    content_type = "text/plain"
    
    client.current_site = GraphSiteData(id=TEST_SITE_ID, name="TestSite", displayName="Test Site", webUrl="...", createdDateTime="...")
    client.current_drive = SharepointSiteDrive(**DRIVE_RESPONSE_A) # id "driveA123"
    # Assume root folder for simplicity, or a specific folder_id could be used
    
    mock_api_response = {"id": "uploadedFileId", "name": file_name, "size": len(file_data)}

    with patch.object(client, 'put', autospec=True) as mock_put:
        mock_put.return_value = MagicMock(spec=Response)
        mock_put.return_value.json.return_value = mock_api_response
        mock_put.return_value.status_code = 201 # Typically 201 Created for uploads
        mock_put.return_value.raise_for_status = MagicMock()

        # Upload to drive root (folder_id is None)
        response_data = client.upload_file(data=file_data, file_name=file_name, content_type=content_type)

        expected_resource = f"/sites/{TEST_SITE_ID}/drives/{DRIVE_RESPONSE_A['id']}/root:/{file_name}:/content"
        mock_put.assert_called_once_with(expected_resource, data=file_data, headers={"Content-Type": content_type})
        assert response_data == mock_api_response

def test_upload_file_with_folder_id(client):
    file_data = b"Another file"
    file_name = "another.txt"
    folder_id_to_upload = "folderToUploadTo123"
    
    client.current_site = GraphSiteData(id=TEST_SITE_ID, name="TestSite", displayName="Test Site", webUrl="...", createdDateTime="...")
    client.current_drive = SharepointSiteDrive(**DRIVE_RESPONSE_A)
    
    with patch.object(client, 'put', autospec=True) as mock_put:
        # ... setup mock_put response ...
        mock_put.return_value = MagicMock(spec=Response, status_code=201, json=MagicMock(return_value={"id":"newFile"}))
        mock_put.return_value.raise_for_status = MagicMock()


        client.upload_file(data=file_data, file_name=file_name, folder_id=folder_id_to_upload)

        expected_resource = f"/sites/{TEST_SITE_ID}/drives/{DRIVE_RESPONSE_A['id']}/items/{folder_id_to_upload}:/{file_name}:/content"
        mock_put.assert_called_once_with(expected_resource, data=file_data, headers={"Content-Type": "text/plain"})

def test_upload_file_http_error(client):
    client.current_site = GraphSiteData(id=TEST_SITE_ID, name="TestSite", displayName="Test Site", webUrl="...", createdDateTime="...")
    client.current_drive = SharepointSiteDrive(**DRIVE_RESPONSE_A)

    with patch.object(client, 'put', autospec=True) as mock_put:
        mock_response = MagicMock(spec=Response)
        mock_response.status_code = 500
        mock_response.text = "Server Error"
        mock_response.request = Request(method="PUT", url="some_url")
        mock_put.return_value = mock_response
        mock_put.return_value.raise_for_status.side_effect = HTTPStatusError(
            "Server Error", request=mock_response.request, response=mock_response
        )

        with pytest.raises(SharepointAPIError) as excinfo: # Expecting SharepointAPIError now
            client.upload_file(data=b"test", file_name="fail.txt")
        assert "HTTP error uploading file: 500" in str(excinfo.value)


def test_upload_file_no_site_or_drive_context(client):
    # client.current_site and client.current_drive are None
    with pytest.raises(SharepointAPIError) as excinfo:
        client.upload_file(data=b"test", file_name="test.txt")
    assert "Site ID and Drive ID are required" in str(excinfo.value)


# --- Tests for download_file ---
@patch('sharepoint_api.core.client.File') # Mock the File class from data_models
@patch('sharepoint_api.core.client.SharePointClient.path')
def test_download_file_success(mock_client_path, mock_file_class, client):
    sharepoint_file_path = "https://tenant.sharepoint.com/sites/MySite/Shared%20Documents/Report.docx"
    target_local_path = "/tmp/downloads"
    file_content_bytes = b"This is the content of the report."
    
    # Mock what client.path(sharepoint_file_path) would return
    mock_drive_file_item = MagicMock(spec=DriveFile)
    mock_drive_file_item.name = "Report.docx"
    mock_drive_file_item.download_url = "https://download.example.com/report_content"
    mock_drive_file_item.size = FileSize(value=len(file_content_bytes))
    mock_drive_file_item.file = FileInfo(mimeType="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    mock_client_path.return_value = mock_drive_file_item
    
    # Mock the response from self.get(download_url)
    mock_download_response = MagicMock(spec=Response)
    mock_download_response.content = file_content_bytes
    mock_download_response.status_code = 200
    mock_download_response.raise_for_status = MagicMock()

    # Mock the File object instantiation and its save method
    mock_file_instance = mock_file_class.return_value
    mock_file_instance.save = MagicMock()

    with patch.object(client, 'get', autospec=True, return_value=mock_download_response) as mock_internal_get:
        downloaded_file_obj = client.download_file(sharepoint_path=sharepoint_file_path, target_path=target_local_path)

        mock_client_path.assert_called_once_with(sharepoint_file_path)
        mock_internal_get.assert_called_once_with(str(mock_drive_file_item.download_url))
        
        expected_save_path = str(Path(target_local_path) / "Report.docx")
        mock_file_class.assert_called_once_with(
            path=expected_save_path,
            data=file_content_bytes,
            name="Report.docx",
            size=len(file_content_bytes),
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        mock_file_instance.save.assert_called_once_with(overwrite=True)
        assert downloaded_file_obj == mock_file_instance

@patch('sharepoint_api.core.client.SharePointClient.path')
def test_download_file_item_not_a_file(mock_client_path, client):
    sharepoint_folder_path = "https://tenant.sharepoint.com/sites/MySite/Shared%20Documents/MyFolder"
    # client.path returns a DriveFolder, not a DriveFile
    mock_client_path.return_value = MagicMock(spec=DriveFolder, name="MyFolder") 
    
    result = client.download_file(sharepoint_path=sharepoint_folder_path)
    assert result is None

@patch('sharepoint_api.core.client.SharePointClient.path')
def test_download_file_no_download_url(mock_client_path, client):
    sharepoint_file_path = "..."
    mock_drive_file_item = MagicMock(spec=DriveFile)
    mock_drive_file_item.name = "FileWithNoUrl.txt"
    mock_drive_file_item.download_url = None # Crucial part: no download URL
    mock_client_path.return_value = mock_drive_file_item
    
    result = client.download_file(sharepoint_path=sharepoint_file_path)
    assert result is None

@patch('sharepoint_api.core.client.SharePointClient.path')
def test_download_file_http_error_on_content_fetch(mock_client_path, client):
    sharepoint_file_path = "..."
    mock_drive_file_item = MagicMock(spec=DriveFile)
    mock_drive_file_item.name = "FileToFail.txt"
    mock_drive_file_item.download_url = "https://faildownload.example.com"
    mock_drive_file_item.size = FileSize(value=100)
    mock_drive_file_item.file = FileInfo(mimeType="text/plain")
    mock_client_path.return_value = mock_drive_file_item

    with patch.object(client, 'get', autospec=True) as mock_internal_get:
        mock_response = MagicMock(spec=Response)
        mock_response.status_code = 403 # Forbidden
        mock_response.text = "Access Denied"
        req = Request(method="GET", url=str(mock_drive_file_item.download_url))
        mock_response.request = req
        mock_internal_get.return_value = mock_response
        mock_internal_get.return_value.raise_for_status.side_effect = HTTPStatusError(
            "Access Denied", request=req, response=mock_response
        )
        
        result = client.download_file(sharepoint_path=sharepoint_file_path)
        assert result is None


# --- Tests for get_shares ---
def test_get_shares_success(client):
    share_url = "https://tenant.sharepoint.com/:x:/s/SiteName/FileId"
    encoded_url = encode_share_link(share_url) # Use the actual function
    mock_item_data = {"id": "sharedItemId", "name": "SharedFile.pptx"}

    with patch.object(client, 'get', autospec=True) as mock_get:
        mock_get.return_value = MagicMock(spec=Response)
        mock_get.return_value.json.return_value = mock_item_data
        mock_get.return_value.status_code = 200
        mock_get.return_value.raise_for_status = MagicMock()

        data = client.get_shares(share_url)

        mock_get.assert_called_once_with(f"/shares/{encoded_url}/driveItem")
        assert data == mock_item_data

def test_get_shares_http_error(client):
    share_url = "https://tenant.sharepoint.com/:x:/s/SiteName/ErrorFileId"
    encoded_url = encode_share_link(share_url)

    with patch.object(client, 'get', autospec=True) as mock_get:
        mock_response = MagicMock(spec=Response)
        mock_response.status_code = 404
        mock_response.text = "Shared item not found"
        req = Request(method="GET", url=f"/shares/{encoded_url}/driveItem")
        mock_response.request = req
        mock_get.return_value = mock_response
        mock_get.return_value.raise_for_status.side_effect = HTTPStatusError(
            "Not Found", request=req, response=mock_response
        )
        
        data = client.get_shares(share_url)
        assert data is None

# --- Tests for upload method ---
@patch('sharepoint_api.core.client.File.from_path') # Mock File.from_path
@patch('sharepoint_api.core.client.SharePointClient.upload_file') # Mock client.upload_file
@patch('sharepoint_api.core.client.SharePointClient.path') # Mock client.path
def test_upload_success(mock_client_path, mock_client_upload_file, mock_file_from_path, client):
    local_file_path = "/path/to/local/file.docx"
    sharepoint_folder_path = "https://tenant.sharepoint.com/sites/MySite/Shared%20Documents/TargetFolder"
    
    # Mock for client.path resolving sharepoint_folder_path
    mock_target_folder_item = MagicMock(spec=DriveFolder)
    mock_target_folder_item.id = "targetFolderId123"
    # Simulate parent reference for site/drive ID resolution if not provided explicitly
    mock_target_folder_item.parent_reference = MagicMock(driveId=TEST_DRIVE_ID, siteId=TEST_SITE_ID)
    mock_client_path.return_value = mock_target_folder_item
    
    # Mock for File.from_path
    mock_local_file_obj = MagicMock()
    mock_local_file_obj.data = b"file content"
    mock_local_file_obj.name = "file.docx"
    mock_local_file_obj.content_type = MagicMock(value="application/msword") # Ensure .value for enum
    mock_file_from_path.return_value = mock_local_file_obj
    
    # Mock for client.upload_file (the one being called internally)
    mock_upload_response = {"id": "newUploadedFileId", "name": "file.docx"}
    mock_client_upload_file.return_value = mock_upload_response

    response = client.upload(local_file_path=local_file_path, sharepoint_path=sharepoint_folder_path)

    mock_client_path.assert_called_once_with(sharepoint_folder_path)
    mock_file_from_path.assert_called_once_with(local_file_path)
    mock_client_upload_file.assert_called_once_with(
        data=mock_local_file_obj.data,
        file_name=mock_local_file_obj.name,
        content_type=mock_local_file_obj.content_type.value,
        site_id=TEST_SITE_ID, # Resolved from parent_reference
        drive_id=TEST_DRIVE_ID, # Resolved from parent_reference
        folder_id=mock_target_folder_item.id
    )
    assert response == mock_upload_response

@patch('sharepoint_api.core.client.SharePointClient.path')
def test_upload_target_not_a_folder(mock_client_path, client):
    # client.path returns a DriveFile, but upload expects a DriveFolder
    mock_client_path.return_value = MagicMock(spec=DriveFile, name="NotAFolder.txt")
    
    response = client.upload(local_file_path="/any/file.txt", sharepoint_path=".../NotAFolder.txt")
    assert response is None

@patch('sharepoint_api.core.client.File.from_path', side_effect=FileNotFoundError("Local file missing"))
@patch('sharepoint_api.core.client.SharePointClient.path')
def test_upload_local_file_not_found(mock_client_path, mock_file_from_path, client):
    mock_client_path.return_value = MagicMock(spec=DriveFolder, id="folderid") # Target path is fine
    
    with pytest.raises(SharepointAPIError) as excinfo:
        client.upload(local_file_path="/nonexistent/file.txt", sharepoint_path="...")
    assert "Local file not found" in str(excinfo.value)

@patch('sharepoint_api.core.client.File.from_path')
@patch('sharepoint_api.core.client.SharePointClient.upload_file', side_effect=SharepointAPIError("Upload failed"))
@patch('sharepoint_api.core.client.SharePointClient.path')
def test_upload_internal_upload_file_fails(mock_client_path, mock_client_upload_file, mock_file_from_path, client):
    mock_client_path.return_value = MagicMock(spec=DriveFolder, id="folderid", parent_reference=MagicMock(siteId="s", driveId="d"))
    mock_file_from_path.return_value = MagicMock(data=b"d", name="n", content_type=MagicMock(value="t"))

    with pytest.raises(SharepointAPIError) as excinfo:
        client.upload(local_file_path="/path/to/file", sharepoint_path="...")
    assert "Upload failed" in str(excinfo.value) # Error from upload_file propagates

@patch('sharepoint_api.core.client.File.from_path')
@patch('sharepoint_api.core.client.SharePointClient.upload_file')
@patch('sharepoint_api.core.client.SharePointClient.path')
def test_upload_explicit_ids_used(mock_client_path, mock_client_upload_file, mock_file_from_path, client):
    explicit_site_id = "explicitSite1"
    explicit_drive_id = "explicitDrive1"
    explicit_folder_id = "explicitFolder1"

    mock_target_folder_item = MagicMock(spec=DriveFolder)
    # ID from path might be different, but explicit folder_id should take precedence
    mock_target_folder_item.id = "pathFolderId" 
    # Parent reference might also exist but should be overridden by explicit site/drive IDs
    mock_target_folder_item.parent_reference = MagicMock(driveId="pathDrive", siteId="pathSite")
    mock_client_path.return_value = mock_target_folder_item
    
    mock_local_file_obj = MagicMock(data=b"data", name="name", content_type=MagicMock(value="type"))
    mock_file_from_path.return_value = mock_local_file_obj
    
    mock_client_upload_file.return_value = {"id": "done"}

    client.upload(
        local_file_path="/local/file", 
        sharepoint_path="...",
        site_id=explicit_site_id,
        drive_id=explicit_drive_id,
        folder_id=explicit_folder_id
    )

    mock_client_upload_file.assert_called_once_with(
        data=b"data",
        file_name="name",
        content_type="type",
        site_id=explicit_site_id,
        drive_id=explicit_drive_id,
        folder_id=explicit_folder_id # Explicit folder_id used
    )

# It's good practice to ensure the test file ends with a newline.
# Add more tests for other methods like get_drive, get_drive_items, path, upload, download_file etc.
# Remember to test edge cases and error conditions. 