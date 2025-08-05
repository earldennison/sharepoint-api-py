#!/usr/bin/env python
"""
Example demonstrating how to use the AsyncSharePointClient
with AsyncOAuth2Client for asynchronous operations.
"""

import asyncio
from sharepoint_api import AsyncSharePointClient
from sharepoint_api.config import SharepointConfig

async def list_sites():
    """List all available SharePoint sites using async client"""
    # Create async client  
    client = AsyncSharePointClient.from_env()
    
    # Get sites
    sites_metadata = await client.get_sites()
    
    print(f"Found {len(sites_metadata.value)} sites:")
    for site in sites_metadata.value:
        print(f"- {site.name}: {site.web_url}")
    
    return sites_metadata

async def get_site_details(site_name):
    """Get details for a specific site"""
    client = AsyncSharePointClient.from_env()
    
    # Get site by name
    site = await client.get_site(site_name=site_name)
    
    if not site:
        print(f"No site found with name: {site_name}")
        return None
    
    # Get drives for the site
    drives = await client.get_drive()
    
    print(f"\nSite details for: {site.name}")
    print(f"URL: {site.web_url}")
    print(f"ID: {site.id}")
    
    if isinstance(drives, list):
        print(f"Drives found: {len(drives)}")
        for drive in drives:
            print(f"- Drive: {drive.name} (ID: {drive.id})")
    else:
        print(f"Drives found: {len(drives.root) if drives else 0}")
        if drives:
            for drive in drives:
                print(f"- Drive: {drive.name} (ID: {drive.id})")
    
    return site, drives

async def main():
    print("=== SharePoint Sites Overview ===")
    await list_sites()
    
    # You can replace this with an actual site name from your tenant
    site_name = "YourSiteName"  
    print(f"\n=== Getting Details for Site: {site_name} ===")
    await get_site_details(site_name)

if __name__ == "__main__":
    asyncio.run(main()) 