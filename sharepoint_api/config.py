import os
import yaml  # type:ignore
from pathlib import Path
from dotenv import load_dotenv
from pydantic import BaseModel
sharepoint_config_path: Path = Path(__file__).parent.parent / ".env"


class SharepointConfig(BaseModel):
    tenant_id: str
    client_id: str
    client_secret: str
    resource_url: str
    resource_url_version: str

    @classmethod
    def from_env(cls) -> "SharepointConfig":
        tenant_id = os.getenv("SHAREPOINT_TENANT_ID")
        client_id = os.getenv("SHAREPOINT_APP_ID")
        client_secret = os.getenv("SHAREPOINT_APP_SECRET")
        resource_url = "https://graph.microsoft.com/"
        resource_url_version = "v1.0"
        assert tenant_id is not None, "SHAREPOINT_TENANT_ID is not set"
        assert client_id is not None, "SHAREPOINT_APP_ID is not set"
        assert client_secret is not None, "SHAREPOINT_APP_SECRET is not set"
        return cls(tenant_id=tenant_id, client_id=client_id, client_secret=client_secret, resource_url=resource_url, resource_url_version=resource_url_version)

    @classmethod
    def from_env_file(cls) -> "SharepointConfig":
        if not sharepoint_config_path.exists():
            raise FileNotFoundError(
                f"Sharepoint config file {sharepoint_config_path} does not exist")
        # load_dotenv(sharepoint_config_path)
        load_dotenv()
        return cls.from_env()

    @classmethod
    def from_config(cls, path: Path = sharepoint_config_path) -> "SharepointConfig":
        if not path.exists():
            raise FileNotFoundError(
                f"Sharepoint config file {path} does not exist")
        with open(path) as file:
            config = yaml.safe_load(file)
            print(config)
            return cls(**config)
