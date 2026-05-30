from fastapi import HTTPException , Depends
from .security import get_current_user
from .models import User

def require_permission(permission: str):
    def permission_checker(
            current_user: User =
            Depends(get_current_user)
    ):
        role_permissions= {
            "admin": [
                "delete_user",
                "ban_user",
                "view_logs"
            ],

            "moderator": [
                "ban_user"
            ],
            "user": []
        }
        permissions = role_permissions.get(current_user.role, [])
        if permission not in permissions:
            raise HTTPException(status_code=403, detail= "Permission denied")
        return current_user
    return permission_checker

