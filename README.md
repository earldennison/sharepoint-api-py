# SharePoint API Client

A modern Python library for interacting with Microsoft SharePoint sites using the Microsoft Graph API. Built with httpx for high-performance async/sync operations, automatic connection management, and streaming support for large files.

## Features

🔄 **Both sync and async clients** with identical APIs  
🚀 **Automatic URL parsing** - just paste SharePoint URLs  
💾 **Streaming support** for large file uploads/downloads  
🔧 **Automatic connection management** with configurable cleanup  
📁 **Rich data models** with comprehensive SharePoint object support  
🛡️ **OAuth2 authentication** via Microsoft Graph API  

## Installation

```bash
pip install sharepoint-api-py
# or
poetry add sharepoint-api-py
```

## Quick Start

### 1. Setup Credentials

Create a `.env` file or set environment variables:

```bash
SHAREPOINT_TENANT_ID="your_tenant_id"
SHAREPOINT_APP_ID="your_app_id"  
SHAREPOINT_APP_SECRET="your_app_secret"
```

### 2. Basic Usage

```python
from sharepoint_api import SharePointClient

# Initialize client from environment
client = SharePointClient.from_env()

# Upload a file - just provide local path and SharePoint folder URL
client.upload(
    "./report.pdf",
    "https://contoso.sharepoint.com/sites/MyTeam/Shared%20Documents/Reports/"
)

# Download a file - just provide SharePoint file URL and local folder
client.download(
    "https://contoso.sharepoint.com/sites/MyTeam/Shared%20Documents/data.xlsx",
    target_path="./downloads/"
)
```

### 3. Async Usage

```python
from sharepoint_api import AsyncSharePointClient

async def main():
    client = AsyncSharePointClient.from_env()
    
    # Same simple API, but async
    await client.upload(
        "./large_dataset.csv",
        "https://contoso.sharepoint.com/sites/MyTeam/Documents/"
    )
    
    await client.download(
        "https://contoso.sharepoint.com/sites/MyTeam/Documents/results.xlsx",
        target_path="./downloads/"
    )
```

## Core Concepts

### Automatic URL Parsing

No need to manually extract site IDs, drive names, or folder paths. Just copy SharePoint URLs from your browser:

```python
# Copy any SharePoint URL from your browser and use it directly
client.upload("./file.pdf", "https://contoso.sharepoint.com/sites/TeamSite/Documents/Reports/")
client.download("https://contoso.sharepoint.com/sites/TeamSite/Documents/file.xlsx", "./downloads/")
```


### Streaming for Large Files

Large files are automatically streamed to avoid memory issues:

```python
# Files larger than threshold (default: 100MB) are automatically streamed
large_file = client.download("https://sharepoint.com/huge_dataset.csv")

# Force streaming for any file
client.download_file(file_obj, use_streaming=True)

# Configure thresholds
client = SharePointClient.from_env(
    large_file_threshold=50*1024*1024,  # 50MB threshold
    auto_close_timeout=60  # Close idle connections after 60s
)
```

## API Reference

### Client Initialization

```python
from sharepoint_api import SharePointClient, AsyncSharePointClient
from sharepoint_api.config import SharepointConfig

# From environment variables
client = SharePointClient.from_env()

# From config object
config = SharepointConfig(
    tenant_id="...",
    client_id="...", 
    client_secret="...",
    resource_url="https://graph.microsoft.com/",
    resource_url_version="v1.0"
)
client = SharePointClient.from_config(config)

# With custom settings
client = SharePointClient.from_env(
    auto_close_timeout=120,  # Close idle connections after 2 minutes
    large_file_threshold=200*1024*1024  # 200MB streaming threshold
)
```

### File and Folder Operations

```python
# Upload files - just provide local path and SharePoint folder URL
client.upload("./document.pdf", "https://sharepoint.com/sites/Team/Documents/Reports/")

# Download files - provide SharePoint file URL and local destination
client.download("https://sharepoint.com/sites/Team/Documents/report.xlsx", "./downloads/")

# Browse folder contents (if needed)
folder = client.path("https://sharepoint.com/sites/Team/Documents/Reports/")
for item in folder.children:
    print(f"📄 {item.name}")
```


## Examples

See the `examples/` directory for complete examples:

- **Basic operations**: Site access, file upload/download
- **Async operations**: Using AsyncSharePointClient  
- **Bulk operations**: Processing multiple files
- **Advanced scenarios**: Custom authentication, error handling

## Contributing

Contributions welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

MIT License - see [LICENSE](LICENSE) for details.

---

**Built with ❤️ using:**
- [httpx](https://www.python-httpx.org/) - Modern HTTP client
- [authlib](https://authlib.org/) - OAuth2 authentication
- [pydantic](https://pydantic.dev/) - Data validation and models