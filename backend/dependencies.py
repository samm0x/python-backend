from fastapi import HTTPException , Depends
from .security import get_current_user
from .models import User


def get_current_admin (user: User = Depends(get_current_user)):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="you are not an admin")

    return {"message": "welcome admin "}

def require_admin(current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    return current_user