from pydantic import BaseModel, Field, HttpUrl, field_validator, RootModel, computed_field
import datetime
from enum import Enum
from typing import Optional, overload, Iterator
from pathlib import Path

from functools import cached_property


class GraphSiteData(BaseModel):
    createdDateTime:datetime.datetime = Field(alias="createdDateTime")
    displayName: str = Field(alias="displayName")
    id: str = Field(alias="id")
    last_modified_date_time: datetime.datetime = Field(alias="lastModifiedDateTime" ,default="")
    name: str = Field(alias="name")
    is_personal_site:bool = Field(alias="isPersonalSite", default=False)
    web_url: str = Field(alias="webUrl")


    
class SiteMetaData(BaseModel):
    odata_context: str = Field(alias="@odata.context")
    odata_nextlink: Optional[str] = Field(alias="@odata.nextLink", default=None)
    value: list[GraphSiteData]


    @overload
    def search(self,web_url:str) -> Optional[GraphSiteData]:
        pass
    @overload
    def search(self,web_url:Optional[str]=None,  name:Optional[str]=None) -> Optional[GraphSiteData]:
        pass
    def search(self,web_url:Optional[str]=None,  name:Optional[str]=None) -> Optional[GraphSiteData]:
        for site in self.value:
            if name and site.name == name and name is not None:
                return site
            if site.web_url == web_url and web_url is not None:
                return site
        return None


class UserInfo(BaseModel):
    email: Optional[str] = None
    id: Optional[str] = None
    display_name: Optional[str] = Field(None, alias='displayName')

class CreatedBy(BaseModel):
    user: Optional[UserInfo] = None

class LastModifiedBy(BaseModel):
    user: Optional[UserInfo] = None

class ParentReference(BaseModel):
    drive_type: Optional[str] = Field(None, alias='driveType')
    drive_id: Optional[str] = Field(None, alias='driveId')
    id: Optional[str] = None
    name: Optional[str] = None
    path: Optional[str] = None
    site_id: Optional[str] = Field(None, alias='siteId')

class FileHashes(BaseModel):
    quick_xor_hash: Optional[str] = Field(None, alias='quickXorHash')

class FileInfo(BaseModel):
    hashes: Optional[FileHashes] = None
    mime_type: Optional[str] = Field(None, alias='mimeType')

class FileSystemInfo(BaseModel):
    created_date_time: Optional[datetime.datetime] = Field(None, alias='createdDateTime')
    last_modified_date_time: Optional[datetime.datetime] = Field(None, alias='lastModifiedDateTime')

class SharedInfo(BaseModel):
    scope: Optional[str] = None

class FolderInfo(BaseModel):
    child_count: Optional[int] = Field(None, alias='childCount')
    

class FileSize(BaseModel):
    value: Optional[int] = None


    def __repr__(self) -> str:
        if self.value is None:
            return "Unknown size"

        if self.value == 0:
            return "0 bytes"

        size = self.value
        units = ["bytes", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB"]
        unit_index = 0
        
        # Keep dividing by 1024 until the size is less than 1024 or we run out of units
        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024.0
            unit_index += 1
        
        # Format to 2 decimal places if it's not bytes, otherwise no decimal places for bytes
        if unit_index > 0:
            return f"{size:.2f} {units[unit_index]}"
        else:
            return f"{int(size)} {units[unit_index]}"


class DriveItem(BaseModel):
    odata_context: Optional[str] = Field(None, alias='@odata.context', exclude=True, repr=False)
    download_url: Optional[HttpUrl] = Field(None, alias='@microsoft.graph.downloadUrl', exclude=True, repr=False)
    created_by: Optional[CreatedBy] = Field(None, alias='createdBy')
    created_date_time: Optional[datetime.datetime] = Field(None, alias='createdDateTime')
    e_tag: Optional[str] = Field(None, alias='eTag', exclude=True, repr=False)
    id: str
    last_modified_by: Optional[LastModifiedBy] = Field(None, alias='lastModifiedBy')
    last_modified_date_time: Optional[datetime.datetime ] = Field(None, alias='lastModifiedDateTime')
    name: Optional[str] = None
    parent_reference: Optional[ParentReference] = Field(None, alias='parentReference')
    web_url: Optional[HttpUrl] = Field(None, alias='webUrl', exclude=True, repr=False)
    c_tag: Optional[str] = Field(None, alias='cTag', exclude=True, repr=False)
    file_system_info: Optional[FileSystemInfo] = Field(None, alias='fileSystemInfo')
    shared: Optional[SharedInfo] = None
    size: FileSize




    @field_validator('size', mode='before')
    @classmethod
    def convert_size_to_filesize_object(cls, v: Optional[int]) -> Optional[FileSize]:
        if v is None:
            return None
        if isinstance(v, int):
            return FileSize(value=v)
        if isinstance(v, FileSize): # Allow FileSize objects to pass through
            return v
        # Pydantic will raise a validation error for other unexpected types
        # based on the Optional[FileSize] type hint for the field.
        return v     

        

    @classmethod
    def from_json(cls, data: dict):
        if data.get("folder") is not None:
            return DriveFolder(**data)
        else:
            return DriveFile(**data)
    

    
class DriveFolder(DriveItem):
    children: list[DriveItem] = Field(default_factory=list)
    folder: Optional[FolderInfo] = None

    def __repr__(self) -> str:
        name_str = self.name if self.name is not None else "Unnamed Folder"
        size_str = repr(self.size) if self.size is not None else "N/A"
        
        # Current folder's line 
        lines = [f"📁 {name_str!r} ({size_str})"]

        num_children = len(self.children)
        for i, child in enumerate(self.children):
            # Recursively call repr(child). This is key.
            # If child is a DriveFolder, its own tree-repr will be called.
            # If child is a file-like DriveItem, its file-repr will be called.
            child_repr_str = repr(child)
            child_repr_lines = child_repr_str.split('\n')

            is_last_child = (i == num_children - 1)
            # Tree branch connectors
            connector = "└── " if is_last_child else "├── "
            # Prefix for subsequent lines of a multi-line child (i.e., a sub-folder's children)
            continuation_prefix = "    " if is_last_child else "│   "

            if child_repr_lines: # Should always be true as repr returns a string
                # Add the first line of the child, prefixed by the connector
                lines.append(connector + child_repr_lines[0])
                
                # Add subsequent lines of the child (if any), prefixed by the continuation_prefix
                for line_idx in range(1, len(child_repr_lines)):
                    lines.append(continuation_prefix + child_repr_lines[line_idx])
        
        return "\n".join(lines)    

class DriveFolderChildren(RootModel):
    root: list[DriveItem]

    def __getitem__(self, item: int | str | slice) -> DriveItem | list[DriveItem]:
        if isinstance(item, slice):
            return self.root[item]
        if isinstance(item, int):
            return self.root[item]
        if isinstance(item, str):
            return [child for child in self.root if child.name == item]
        return self.root[item]
    
    def __iter__(self) -> Iterator[DriveItem]:
        return iter(self.root)
    
    def __len__(self) -> int:
        return len(self.root)
    
    def __contains__(self, item_name: str) -> bool:
        return any(child.name == item_name for child in self.root)

class SharepointSiteDrive(BaseModel):
    created_date: Optional[datetime.datetime] = Field(alias="createdDateTime")
    description: Optional[str] = None
    id: str
    last_modified_date: Optional[datetime.datetime] = Field(alias="lastModifiedDateTime")
    name: str
    web_url: HttpUrl = Field(alias="webUrl")
    drive_type: Optional[str] = Field(alias="driveType")
    created_by: Optional[UserInfo] = Field(alias="createdBy")
    last_modified_by: Optional[UserInfo] = Field(
        alias="lastModifiedBy", default="")
    owner: Optional[UserInfo] = Field(alias="owner")
    quota: dict
    

    @computed_field
    @cached_property
    def drive_alias(self) -> str:
        return unquote(urlparse(str(self.web_url)).path.split('/')[-1])

class SharepointSiteDrives(RootModel):
    root: list[SharepointSiteDrive]

    def __iter__(self):
        return iter(self.root)

    def __getitem__(self, item:int | str):
        if isinstance(item, int):
            return self.root[item]
        elif isinstance(item, str):
            return next((drive for drive in self.root if drive.name == item), None)
        else:
            raise ValueError(f"Invalid type: {type(item)}")
    
    def __repr__(self) -> str:
        string = ""
        for drive in self.root:
            string += f"{drive.name}\n"
        return string
    
    def get_drive(self, item:int | str):
        if isinstance(item, int):
            return self.root[item]
        elif isinstance(item, str):
            drive = next((drive for drive in self.root if drive.name == item), None)
        
            if drive is None:
                drive = next((drive for drive in self.root if drive.drive_alias == item), None)
        
        if drive is None:
            print(f"Drive {item} not found")
            return None
        return drive
    

class DriveFile(DriveItem):
    file: Optional[FileInfo] = None

    def __repr__(self) -> str:
        base_str = f"📄 {self.name} [File] {self.size.__repr__()}"
        return base_str


from urllib.parse import urlparse, parse_qs, unquote

class SharepointDrivePath(BaseModel):
    name:str
    path:str
    file_id:Optional[str] = None

class SharePointUrl(BaseModel):
    full_url:str
    host_name:str
    site_name:str
    drive:SharepointDrivePath = Field(..., description="Drive path is the combination of the drive and the folder path")
    is_direct_file:bool = False

    @computed_field
    @property
    def relative_server_url(self) -> str:
        return f"{self.host_name}:/sites/{self.site_name}"


    @classmethod
    def from_weburl(cls, weburl:str):
        parsed_url = urlparse(weburl)
        netloc = parsed_url.netloc
        #path = parse_qs(parsed_url.query)['id'][0]
        path = parsed_url.path
        if "/:x:/s/" in path:
            is_direct_file = True
        else:
            is_direct_file = False
        file_id = None

        path_list = path.split('/')
        print(parsed_url.query)
        query_params = parse_qs(parsed_url.query)
        if "id" in query_params:
            true_path = query_params['id'][0]
            true_path = "/".join(true_path.split("/")[4:])
        else:
            true_path = path
            true_path = "/".join([unquote(c) for c in true_path.split("/")[4:]])

        if path_list[1] == 'sites':
            site_name =  path_list[2]
            if len(path_list) > 3:
                drive_name = path_list[3]
                drive_name = unquote(drive_name)
            else:
                drive_name = None
        elif "/:x:/s/" in path:
            path_list = path.split("/:x:/s/")[1]
            path_list = path_list.split("/")
            drive_name = ""
            file_id = path_list[1]
            site_name = path_list[0]
        else:
            site_name = path_list[1]
        
        if file_id is not None:
            drive = SharepointDrivePath(name=drive_name, path=true_path, file_id=file_id)
        else:
            drive = SharepointDrivePath(name=drive_name, path=true_path)

        return cls(full_url=weburl, host_name=netloc, site_name=site_name, drive=drive, is_direct_file=is_direct_file)


    def __repr__(self):
        return f"SharePointUrl(host_name={self.host_name}, site_name={self.site_name}, drive={self.drive})"
    

class SharepointSite(BaseModel):
    id: str
    created_date: str = Field(alias="createdDateTime")
    last_modified_date: str = Field(alias="lastModifiedDateTime", default="")
    name: str
    web_url: str = Field(alias="webUrl")
    root: dict
    site_collection: Optional[dict] = None

class ContentTypes(Enum):
    TEXT = "text/plain"
    EXCEL = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    PDF = "application/pdf"
    WORD = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    POWERPOINT = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    IMAGE = "image/jpeg"
    AUDIO = "audio/mpeg"
    JSON = "application/json"
    CSV = "text/csv"
    TSV = "text/tab-separated-values"
    XML = "application/xml"
    HTML = "text/html"
    ZIP = "application/zip"
    RAR = "application/x-rar-compressed"
    _7Z = "application/x-7z-compressed"
    TAR = "application/x-tar"
    GZ = "application/gzip"
    BZ2 = "application/x-bzip2"
    XZ = "application/x-xz"
    WIM = "application/x-wim"
    ISO = "application/x-iso9660-image"

    @classmethod
    def reverse_lookup(cls, file_type:str) -> "ContentTypes":
        return next((content_type for content_type in cls if content_type.value == file_type), None)

class File(BaseModel):
    path:str
    data:Optional[bytes]  # Allow None for streaming downloads
    name:str
    size: FileSize
    content_type:ContentTypes = Field(default=ContentTypes.TEXT)

    @field_validator('size', mode='before')
    @classmethod
    def convert_size(cls, v:int) -> int:
        if v is None:
            return 0
        
        elif isinstance(v, int):
            return FileSize(value=v)
        elif isinstance(v, FileSize):
            return v
        Warning(f"Size {v} is not an integer, defaulting to 0")

    @field_validator('content_type', mode='before')
    @classmethod
    def lookup_type(cls, v:str) -> ContentTypes:
        ctypes = ContentTypes.reverse_lookup(v)
        if ctypes is None:
            Warning(f"Content type {v} not found, defaulting to TEXT")
            return ContentTypes.TEXT
        return ctypes

    def save(self, path:str=None, overwrite:bool=True):
        if path is None:
            path = self.path
        if Path(path).exists() and not overwrite:
            raise FileExistsError(f"File {path} already exists")
        
        # Skip writing if data is None (for streaming downloads)
        if self.data is not None:
            Path(path).write_bytes(self.data)
        else:
            # For streaming downloads, file already exists at path
            if not Path(path).exists():
                raise ValueError(f"File {path} was expected to exist for streaming download but does not")
        return path


    @classmethod
    def from_path(self, path:str) -> "File":
        name = Path(path).name
        file_extension = Path(path).suffix

        match file_extension:
            case ".txt":
                content_type = ContentTypes.TEXT
            case ".xlsx" | ".xls":
                content_type = ContentTypes.EXCEL
            case ".pdf":
                content_type = ContentTypes.PDF
            case ".docx" | ".doc":
                content_type = ContentTypes.WORD
            case ".pptx" | ".ppt":
                content_type = ContentTypes.POWERPOINT
            case ".jpg" | ".jpeg" | ".png" | ".gif" | ".bmp" | ".tiff" | ".ico":
                content_type = ContentTypes.IMAGE
            case ".mp3" | ".wav" | ".ogg" | ".m4a" | ".flac":
                content_type = ContentTypes.AUDIO
            case ".json":
                content_type = ContentTypes.JSON
            case ".csv":
                content_type = ContentTypes.CSV
            case ".tsv":
                content_type = ContentTypes.TSV
            case ".xml":
                content_type = ContentTypes.XML
            case ".html":
                content_type = ContentTypes.HTML
            case ".zip":
                content_type = ContentTypes.ZIP
            case ".rar":
                content_type = ContentTypes.RAR
            case ".7z":
                content_type = ContentTypes._7Z
            case ".tar":
                content_type = ContentTypes.TAR
            case ".gz":
                content_type = ContentTypes.GZ
            case ".bz2":
                content_type = ContentTypes.BZ2
            case ".xz":
                content_type = ContentTypes.XZ
            case ".wim":
                content_type = ContentTypes.WIM
            case ".iso":
                content_type = ContentTypes.ISO
            case _:
                content_type = ContentTypes.TEXT
        data = Path(path).read_bytes()
        size = len(data)
        return File(path=path, data=data, content_type=content_type, name=name, size=size)


    def __repr__(self) -> str:
        name = self.path if self.path else self.name
        return f"File({name}, content_type={self.content_type})"
    

class SiteSession(BaseModel):
    site: GraphSiteData
    share_point_url: SharePointUrl
    drive: Optional[SharepointSiteDrive] = None


    