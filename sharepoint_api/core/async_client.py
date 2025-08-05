#%%
from authlib.integrations.httpx_client import AsyncOAuth2Client, OAuth2Auth
from httpx import AsyncClient, HTTPStatusError, Limits, Timeout
from typing import Optional, overload, Union
from pathlib import Path
import time
import asyncio
from sharepoint_api.config import SharepointConfig
from sharepoint_api.logging import logger
from sharepoint_api.core.data_models import (
    GraphSiteData, DriveItem, DriveFolder, DriveFile, SharePointUrl,
    SharepointSiteDrive, SharepointSiteDrives,
    File, SiteMetaData
)
from sharepoint_api.core.errors import SharepointAPIError

import base64
def encode_share_link(share_url: str) -> str:
    """
    Encodes a sharing URL into a share ID compatible with Microsoft Graph.
    """
    encoded_bytes = base64.urlsafe_b64encode(share_url.encode("utf-8"))
    encoded_url = encoded_bytes.decode("utf-8").rstrip("=")
    return "u!" + encoded_url


class AsyncSharePointBaseClient(AsyncClient):
    current_site: Optional["GraphSiteData"] = None
    current_drive: Optional["SharepointSiteDrive"] = None
    
    def __init__(self, client_id:str, client_secret:str, resource_url:str, resource_url_version:str, tenant_id:str,
                retry:int = 5, backoff_factor:float = 0.5, auto_close_timeout:int = 30, 
                large_file_threshold:int = 100*1024*1024
                 ):
        logger.info(f"Initializing AsyncSharePointClient for tenant {tenant_id}")
        
        # Auto-cleanup configuration
        self.auto_close_timeout = auto_close_timeout
        self.large_file_threshold = large_file_threshold
        self._last_activity = None
        
        self._auth_client = AsyncOAuth2Client(
            client_id=client_id,
            client_secret=client_secret,
            token_endpoint=f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token",
        )
        
        # Enhanced httpx configuration
        limits = Limits(
            max_keepalive_connections=20,
            max_connections=100,
            keepalive_expiry=auto_close_timeout
        )
        
        timeout = Timeout(
            connect=5.0,
            read=30.0,
            write=10.0,
            pool=60.0
        )
        
        super().__init__(
            base_url=f"{resource_url}{resource_url_version}",
            limits=limits,
            timeout=timeout,
            http2=False  # Disable HTTP/2 for now (requires h2 package)
        )
        
        # Store auth details for token fetching
        self._client_id = client_id
        self._client_secret = client_secret
        self._tenant_id = tenant_id
        self._resource_url = resource_url
        self._access_token = None
        
        self._update_activity()
    
    async def _ensure_token(self):
        """Ensure we have a valid access token"""
        if self._access_token is None:
            logger.info(f"Fetching initial token for tenant {self._tenant_id}")
            token_data = await self._auth_client.fetch_token(
                url=f"https://login.microsoftonline.com/{self._tenant_id}/oauth2/v2.0/token",
                grant_type="client_credentials",
                scope=self._resource_url + ".default"
            )
            self._access_token = token_data.get('access_token')
            self.headers.update({'Authorization': f'Bearer {self._access_token}'})
    
    def _update_activity(self):
        """Update last activity timestamp"""
        self._last_activity = time.time()
        
    async def _auto_cleanup_if_needed(self, operation_size: int = 0):
        """Auto-cleanup connections based on activity and file size"""
        if self._last_activity is None:
            return
            
        now = time.time()
        idle_time = now - self._last_activity
        
        # Close if idle too long or after large file operations
        should_close = (
            idle_time > self.auto_close_timeout or 
            operation_size > self.large_file_threshold
        )
        
        if should_close:
            logger.debug(f"Auto-closing async client: idle_time={idle_time:.1f}s, operation_size={operation_size}")
            try:
                await self.aclose()
            except Exception as e:
                logger.warning(f"Error during async auto-cleanup: {e}")

    async def request(self, method: str, url: str, **kwargs):
        """Override request to ensure token and update activity"""
        await self._ensure_token()
        self._update_activity()
        return await super().request(method, url, **kwargs)


class AsyncSharePointClient(AsyncSharePointBaseClient):
    def __init__(self, client_id:str, client_secret:str, resource_url:str, resource_url_version:str, tenant_id:str,
                retry:int = 5, backoff_factor:float = 0.5, auto_close_timeout:int = 30, 
                large_file_threshold:int = 100*1024*1024
                 ):
        super().__init__(client_id, client_secret, resource_url, resource_url_version, tenant_id, 
                        retry, backoff_factor, auto_close_timeout, large_file_threshold)
    
    async def get_sites(self, search:str = None, **kwargs) -> SiteMetaData:
        if search:
            kwargs['search'] = search
        response = await self.get('/sites', params=kwargs)
        data = response.json()
        return SiteMetaData(**data)
    
    @classmethod
    def from_config(cls, config:SharepointConfig, **kwargs) -> "AsyncSharePointClient":
        return cls(
            client_id=config.client_id,
            client_secret=config.client_secret,
            resource_url=config.resource_url,
            resource_url_version=config.resource_url_version,
            tenant_id=config.tenant_id,
            **kwargs  # Allow auto_close_timeout, large_file_threshold, etc.
        )
    @classmethod
    def from_env(cls, **kwargs) -> "AsyncSharePointClient":
        config = SharepointConfig.from_env()
        return cls.from_config(config, **kwargs)

    @overload
    async def get_site(self, site_id:str) -> Optional[GraphSiteData]:
        pass
    
    @overload
    async def get_site(self, web_url:str) -> Optional[GraphSiteData]:
        pass
    
    async def get_site(self, site_name:str=None, site_id:str = None, web_url:str = None) -> Optional[GraphSiteData]:
        if site_id:
            try:
                response = await self.get(f"/sites/{site_id}")
                response.raise_for_status()
                site_data = response.json()
                self.current_site = GraphSiteData(**site_data)
                return self.current_site
            except HTTPStatusError as e:
                logger.error(f"HTTP error fetching site by ID {site_id}: {e.response.status_code} - {e.response.text}")
                return None
            except Exception as e:
                logger.error(f"Error processing site data for ID {site_id}: {e}")
                return None
                
        if site_name:
            sites_meta_data = await self.get_sites()
            site = sites_meta_data.search(name=site_name)
            if site is None:
                logger.info(f"Site {site_name} not found by name")
            else:
                self.current_site = site
            return site

        if web_url:
            try:
                parsed_sp_url = SharePointUrl.from_weburl(web_url)
                response = await self.get(f"/sites/{parsed_sp_url.relative_server_url}")
                response.raise_for_status()
                site_data = response.json()
                self.current_site = GraphSiteData(**site_data)
                return self.current_site
            except HTTPStatusError as e:
                logger.warning(f"HTTP error fetching site by web URL direct lookup '{web_url}': {e.response.status_code}. Attempting search.")
                sites_meta_data = await self.get_sites()
                site = sites_meta_data.search(web_url=web_url)
                if site:
                    self.current_site = site
                else:
                    logger.info(f"Site with web_url '{web_url}' not found via search either.")
                return site
            except Exception as e:
                logger.error(f"Error processing site data for web URL {web_url} (direct lookup): {e}")
                logger.info(f"Attempting to find site by web_url '{web_url}' via search as fallback.")
                sites_meta_data = await self.get_sites()
                site = sites_meta_data.search(web_url=web_url)
                if site:
                    self.current_site = site
                return site
        
        logger.info("No valid parameters (site_id, site_name, or web_url) provided to get_site.")
        return None

    async def get_drive(self, site_id:str=None, drive_id:str=None, drive_name:str=None) -> Union[Optional[SharepointSiteDrive], SharepointSiteDrives]:
        resolved_site_id = site_id
        if resolved_site_id is None and self.current_site:
            resolved_site_id = self.current_site.id

        if not resolved_site_id:
            logger.error("Cannot get drive without a site_id or current_site context.")
            return None

        if drive_id:
            try:
                response = await self.get(f"/sites/{resolved_site_id}/drives/{drive_id}")
                response.raise_for_status()
                drive_data = response.json()
                drive = SharepointSiteDrive(**drive_data)
                if drive_name and drive.name != drive_name:
                    logger.warning(f"Drive found by ID {drive_id} has name '{drive.name}', but user specified name '{drive_name}'.")
                self.current_drive = drive
                return drive
            except HTTPStatusError as e:
                logger.error(f"HTTP error fetching drive by ID {drive_id} for site {resolved_site_id}: {e.response.status_code} - {e.response.text}")
                return None
            except Exception as e:
                logger.error(f"Error processing drive data for drive ID {drive_id}, site {resolved_site_id}: {e}")
                return None
        
        try:
            response = await self.get(f"/sites/{resolved_site_id}/drives")
            response.raise_for_status()
            drives_data = response.json()['value']
            all_drives = SharepointSiteDrives(root=[SharepointSiteDrive(**d) for d in drives_data])
        except HTTPStatusError as e:
            logger.error(f"HTTP error fetching all drives for site {resolved_site_id}: {e.response.status_code} - {e.response.text}")
            return None
        except Exception as e:
            logger.error(f"Error processing drives list for site {resolved_site_id}: {e}")
            return None

        if drive_name:
            drive = all_drives.get_drive(drive_name)
            if drive:
                self.current_drive = drive
            else:
                logger.info(f"Drive with name '{drive_name}' not found in site {resolved_site_id}.")
            return drive
        
        return all_drives

    async def get_drive_items(self, site_id:str=None, drive_id:str=None, item_id:str=None, path:str=None) -> Optional[DriveItem]:
        """Get drive items by ID or path. Returns None if not found or error occurs."""
        resolved_site_id = site_id
        if resolved_site_id is None and self.current_site:
            resolved_site_id = self.current_site.id

        resolved_drive_id = drive_id
        if resolved_drive_id is None and self.current_drive:
            resolved_drive_id = self.current_drive.id
        
        if not resolved_site_id or not resolved_drive_id:
            logger.error("Cannot get drive items without site_id and drive_id.")
            return None

        try:
            if item_id and path:
                response = await self.get(f"/sites/{resolved_site_id}/drives/{resolved_drive_id}/items/{item_id}:/{path.lstrip('/')}")
            elif item_id:
                response = await self.get(f"/sites/{resolved_site_id}/drives/{resolved_drive_id}/items/{item_id}")
            elif path:
                response = await self.get(f"/sites/{resolved_site_id}/drives/{resolved_drive_id}/root:/{path.lstrip('/')}")
            else:
                response = await self.get(f"/sites/{resolved_site_id}/drives/{resolved_drive_id}/root")
            
            response.raise_for_status()
            item_data = response.json()
            
            if not item_data:
                logger.warning(f"No item data returned for query (site_id={resolved_site_id}, drive_id={resolved_drive_id}, item_id={item_id}, path={path}) despite 2xx status.")
                return None
            
            item = DriveItem.from_json(item_data)

            if isinstance(item, DriveFolder):
                children_response = await self.get(f"/sites/{resolved_site_id}/drives/{resolved_drive_id}/items/{item.id}/children")
                children_response.raise_for_status()
                children_data = children_response.json().get('value', [])
                item.children = [DriveItem.from_json(child) for child in children_data]
            return item

        except HTTPStatusError as e:
            logger.error(f"HTTP error getting drive item (site_id={resolved_site_id}, drive_id={resolved_drive_id}, item_id={item_id}, path={path}): {e.response.status_code} - {e.response.text}", exc_info=False)
            return None
        except Exception as e: 
            logger.error(f"Error processing drive item (site_id={resolved_site_id}, drive_id={resolved_drive_id}, item_id={item_id}, path={path}): {e}", exc_info=True)
            return None

    async def path(self, path:str) -> Optional[DriveItem]:
        url = SharePointUrl.from_weburl(path)
        if url.is_direct_file:
            try:
                shared_item_data = await self.get_shares(url.full_url)
                if shared_item_data:
                    return DriveItem.from_json(shared_item_data)
                return None
            except Exception as e:
                logger.error(f"Error parsing shared file data for path {path}: {e}")
                return None

        site = await self.get_site(web_url=path)
        if not site:
            logger.error(f"Could not determine site from path: {path}")
            return None
        
        drive = await self.get_drive(site_id=site.id, drive_name=url.drive.name)
        if not isinstance(drive, SharepointSiteDrive):
            logger.error(f"Could not determine a unique drive '{url.drive.name}' for site '{site.name}' from path: {path}")
            return None
        
        item = await self.get_drive_items(site_id=site.id, drive_id=drive.id, path=url.drive.path)
        return item

    async def get_shares(self, share_url:str) -> Optional[dict]:
        enc = encode_share_link(share_url)
        try:
            response = await self.get(f"/shares/{enc}/driveItem")
            response.raise_for_status()
            return response.json()
        except HTTPStatusError as e:
            logger.error(f"HTTP error getting shared item from URL {share_url}: {e.response.status_code} - {e.response.text}", exc_info=False)
            return None
        except Exception as e:
            logger.error(f"Error processing shared item from URL {share_url}: {e}", exc_info=True)
            return None

    async def download(self, sharepoint_path:str, target_path:str=None) -> Optional[File]:
        try:
            self._update_activity()
            share_point_item = await self.path(sharepoint_path)
            
            if not isinstance(share_point_item, DriveFile):
                logger.error(f"Path '{sharepoint_path}' did not resolve to a downloadable file. Resolved to: {type(share_point_item)}")
                return None
            
            if not share_point_item.download_url:
                logger.error(f"File '{share_point_item.name}' does not have a download URL.")
                return None

            if target_path is None:
                target_path = "./" 
            
            file_obj = await self.download_file(share_point_item, target_path)
            
            # Get file size for auto-cleanup decision
            file_size = file_obj.size.value if file_obj and hasattr(file_obj, 'size') and file_obj.size else 0
            return file_obj
            
        except HTTPStatusError as e:
            logger.error(f"HTTP error downloading file content from {share_point_item.download_url}: {e.response.status_code} - {e.response.text}", exc_info=False)
            return None
        except Exception as e:
            logger.error(f"Error during download or save of file '{share_point_item.name}' from {sharepoint_path}: {e}", exc_info=True)
            return None
        finally:
            # Auto-cleanup after download
            file_size = file_obj.size.value if 'file_obj' in locals() and file_obj and hasattr(file_obj, 'size') and file_obj.size else 0
            await self._auto_cleanup_if_needed(file_size)

    async def download_file(self, share_point_file:DriveFile, target_path:str=None, use_streaming:bool=None) -> Optional[File]:
        if target_path is None:
            target_path = "./"
        final_save_path = Path(target_path)
        if final_save_path.is_dir():
            final_save_path = final_save_path / share_point_file.name

        # Auto-detect streaming for large files
        file_size = share_point_file.size.value if share_point_file.size and share_point_file.size.value else 0
        if use_streaming is None:
            use_streaming = file_size > self.large_file_threshold
        
        mime_type = "application/octet-stream"
        if share_point_file.file and share_point_file.file.mime_type:
            mime_type = share_point_file.file.mime_type
            
        if use_streaming:
            logger.debug(f"Using async streaming download for {share_point_file.name} ({file_size} bytes)")
            # Stream download directly to file
            async with self.stream('GET', str(share_point_file.download_url)) as response:
                response.raise_for_status()
                with open(final_save_path, 'wb') as f:
                    async for chunk in response.aiter_bytes(chunk_size=8192):
                        f.write(chunk)
            
            # Create File object without loading data into memory
            file_obj = File(
                path=str(final_save_path),
                data=None,  # Don't load large files into memory
                name=share_point_file.name,
                size=file_size,
                content_type=mime_type
            )
        else:
            # In-memory download for smaller files
            response = await self.get(str(share_point_file.download_url))
            response.raise_for_status()
            file_data = response.content
            
            file_obj = File(
                path=str(final_save_path), 
                data=file_data, 
                name=share_point_file.name, 
                size=file_size,
                content_type=mime_type 
            )
            file_obj.save(overwrite=True)
            
        return file_obj

    async def upload_file(self, data: bytes, file_name: str, content_type: str = "text/plain", site_id:Optional[str]=None, drive_id:Optional[str]=None, folder_id:Optional[str]=None, use_streaming:bool=None) -> Optional[dict]:
        resolved_site_id = site_id or (self.current_site.id if self.current_site else None)
        resolved_drive_id = drive_id or (self.current_drive.id if self.current_drive else None)
        resolved_folder_id = folder_id

        if not resolved_site_id or not resolved_drive_id:
            logger.error("upload_file requires site_id and drive_id to be resolved.")
            from sharepoint_api.core.errors import SharepointAPIError
            raise SharepointAPIError("Site ID and Drive ID are required and could not be resolved for upload.")

        if resolved_folder_id:
            resource = f"/sites/{resolved_site_id}/drives/{resolved_drive_id}/items/{resolved_folder_id}:/{file_name}:/content"
        else:
            resource = f"/sites/{resolved_site_id}/drives/{resolved_drive_id}/root:/{file_name}:/content"

        # Auto-detect streaming for large files
        data_size = len(data) if data else 0
        if use_streaming is None:
            use_streaming = data_size > self.large_file_threshold

        logger.info(f"Uploading file {file_name} to SharePoint target: {resource} (size: {data_size} bytes, streaming: {use_streaming})")
        headers = {"Content-Type": content_type}
        
        try:
            if use_streaming and data_size > 0:
                logger.debug(f"Using async streaming upload for {file_name} ({data_size} bytes)")
                # For large files, use streaming upload
                from io import BytesIO
                async with self.stream('PUT', resource, content=BytesIO(data), headers=headers) as response:
                    response.raise_for_status()
                    upload_result = response.json() if response.content else {}
            else:
                # Standard upload for smaller files
                response = await self.put(resource, data=data, headers=headers)
                response.raise_for_status()
                upload_result = response.json()
            
            logger.info(f"File {file_name} uploaded successfully to SharePoint")
            
            # Auto-cleanup after large upload
            await self._auto_cleanup_if_needed(data_size)
            
            return upload_result
            
        except HTTPStatusError as e:
            logger.error(
                f"HTTP error uploading file {file_name} to {resource}: {e.response.status_code} - {e.response.text}", exc_info=False)
            from sharepoint_api.core.errors import SharepointAPIError
            raise SharepointAPIError(f"HTTP error uploading file: {e.response.status_code} - {e.response.text}")
        except Exception as e: 
            logger.error(
                f"Error uploading file {file_name} to {resource}: {str(e)}", exc_info=True)
            from sharepoint_api.core.errors import SharepointAPIError
            raise SharepointAPIError(f"Error uploading file: {str(e)}")

    async def upload(self, file_path: str, sharepoint_path: str, site_id: Optional[str] = None, drive_id: Optional[str] = None, folder_id: Optional[str] = None) -> Optional[dict]:
        """Upload a local file to SharePoint using file path and SharePoint URL"""
        try:
            self._update_activity()
            share_point_target_item = await self.path(sharepoint_path)
            
            if not isinstance(share_point_target_item, DriveFolder):
                logger.error(f"SharePoint path '{sharepoint_path}' is not a folder. Resolved to: {type(share_point_target_item)}")
                return None 

            from pathlib import Path
            local_file_path = Path(file_path)
            if not local_file_path.exists():
                logger.error(f"Local file {file_path} does not exist")
                from sharepoint_api.core.errors import SharepointAPIError
                raise SharepointAPIError(f"Local file {file_path} does not exist")
            
            try:
                file_data = local_file_path.read_bytes()
            except Exception as e:
                logger.error(f"Error reading local file {file_path}: {e}")
                from sharepoint_api.core.errors import SharepointAPIError
                raise SharepointAPIError(f"Error reading local file {file_path}: {e}")
            
            target_folder_id = folder_id or share_point_target_item.id
            
            final_site_id = site_id
            if final_site_id is None and hasattr(self, 'current_site') and self.current_site:
                final_site_id = self.current_site.id
            elif final_site_id is None:
                logger.error("No site context available for upload")
                from sharepoint_api.core.errors import SharepointAPIError
                raise SharepointAPIError("Site ID could not be resolved for upload")
            
            final_drive_id = drive_id
            if final_drive_id is None and hasattr(self, 'current_drive') and self.current_drive:
                final_drive_id = self.current_drive.id
            elif final_drive_id is None:
                logger.error("No drive context available for upload")
                from sharepoint_api.core.errors import SharepointAPIError
                raise SharepointAPIError("Drive ID could not be resolved for upload")
            
            # Use upload_file method with the file data
            return await self.upload_file(
                data=file_data,
                file_name=local_file_path.name,
                content_type="application/octet-stream",  # Let SharePoint detect content type
                site_id=final_site_id, 
                drive_id=final_drive_id, 
                folder_id=target_folder_id
            )
            
        except Exception as e:
            logger.error(f"Error during upload from {file_path} to {sharepoint_path}: {e}")
            from sharepoint_api.core.errors import SharepointAPIError
            raise SharepointAPIError(f"Upload failed: {str(e)}")

    def __repr__(self) -> str:
        return f"AsyncSharePointClient()"