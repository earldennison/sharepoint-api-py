# Async SharePoint API Examples

This directory contains examples of using the AsyncSharePointClient with AsyncOAuth2Client for asynchronous operations with SharePoint.

## Setup

Before running the examples, ensure you have set up the necessary environment variables:

```bash
export SHAREPOINT_TENANT_ID="your_tenant_id"
export SHAREPOINT_APP_ID="your_client_id"
export SHAREPOINT_APP_SECRET="your_client_secret"
```

## Examples

### Basic Async Usage

The `async_example.py` file demonstrates:

1. Creating an AsyncSharePointClient instance
2. Listing all sites asynchronously
3. Getting details about a specific site
4. Working with drives in a SharePoint site

To run the example:

```bash
python examples/async_example.py
```

## Key Benefits of Using AsyncOAuth2Client

1. **Improved Performance**: Handle multiple SharePoint operations concurrently
2. **Resource Efficiency**: Better resource utilization with non-blocking I/O
3. **Modern Code**: Uses Python's modern async/await syntax
4. **Automatic Token Management**: Handles OAuth token acquisition and renewal automatically

## Sample Code

```python
import asyncio
from sharepoint_api.api import AsyncSharePointClient
from sharepoint_api.config import SharepointConfig

async def example():
    config = SharepointConfig.from_env()
    client = AsyncSharePointClient(config)
    
    # Run multiple operations concurrently
    sites_task = client.get("/sites")
    users_task = client.get("/users")
    
    sites, users = await asyncio.gather(sites_task, users_task)
    return sites, users

# Run the async function
asyncio.run(example())
```

## Converting Synchronous Code to Async

If you're transitioning from the synchronous SharePointClient, the main changes are:

1. Use `await` when calling client methods
2. Run your code within an async function
3. Use `asyncio.run()` to start the async event loop
4. Consider using `asyncio.gather()` for concurrent operations 