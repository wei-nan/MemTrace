from typing import Any, Dict, Optional, Union
from .config import settings

class AnonymousUser:
    """Represents an unauthenticated guest. 
    Operations requiring identity should reject this type.
    """
    id: None = None
    email: None = None
    is_anonymous: bool = True
    is_admin: bool = False
    
    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)


def can_anonymous_view(workspace: Union[Dict[str, Any], Any]) -> bool:
    """
    Determines if an anonymous guest can browse this workspace.
    Both conditions must be met:
    1. Deployment allows anonymous access (env var)
    2. Workspace explicitly enables anonymous view
    """
    allow_view = False
    if isinstance(workspace, dict):
        allow_view = workspace.get("allow_anonymous_view", False)
    else:
        allow_view = getattr(workspace, "allow_anonymous_view", False)

    return (
        settings.allow_anonymous
        and bool(allow_view)
    )
