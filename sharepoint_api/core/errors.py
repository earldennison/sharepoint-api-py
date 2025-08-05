
class SharepointAPIError(Exception):
    """Base exception for SharePoint API errors"""
    pass


class AuthenticationError(SharepointAPIError):
    """Exception raised when authentication fails"""
    pass


class ResourceNotFoundError(SharepointAPIError):
    """Exception raised when a requested resource is not found"""
    pass
