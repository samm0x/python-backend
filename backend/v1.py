from fastapi import APIRouter, HTTPException, Depends, Request
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordRequestForm
from .models import User, RefreshToken, TokenBlacklist
from .permissions import require_permission
from .schemas import RegisterRequest, UserRequest, LoginResponse
from .database import get_db
from .security import (
    hash_password, create_reset_token,
    get_current_user, oauth2_scheme,
    get_current_session_id, log_action
)
from datetime import datetime, timedelta
from .dependencies import get_current_admin
from jose import jwt
from slowapi import Limiter
from slowapi.util import get_remote_address
from backend.services.auth_services import login, refresh_token_endpoint as refresh_service
from backend.config import settings
from fastapi import UploadFile , File
import shutil
import os
import json
from backend.core.redis import redis_client

limiter = Limiter(key_func=get_remote_address)
router = APIRouter()

SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM


@router.post("/login", response_model=LoginResponse)
@limiter.limit("5 / minute")
def logins(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    return login(request, db, form_data.username, form_data.password)


@router.post("/register")
def register(request: Request, data: RegisterRequest, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.username == data.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="User already exists")
    from .security import hash_password
    user = User(username=data.username, password=hash_password(data.password), role="user")
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"message": "User registered successfully"}


@router.post("/refresh")
def refresh_token_endpoint(refresh_token: str, db: Session = Depends(get_db)):
    return refresh_service(db, refresh_token)


@router.post("/logout_everywhere")
def logout_everywhere(token: str = Depends(oauth2_scheme), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    blacklisted_token = TokenBlacklist(token=token)
    db.query(RefreshToken).filter(
        RefreshToken.user_id == user.id,
        RefreshToken.is_revoked == False
    ).update({"is_revoked": True})
    db.add(blacklisted_token)
    db.commit()
    return {"message": "Logged out from all devices"}


@router.get("/me", response_model=UserRequest)
def get_me(user: User = Depends(get_current_user)):
    return user


@router.get("/profile")
def profile(request: Request , user:User = Depends(get_current_user)):
    cache_key = f"profile:{user.id}"

    ceched_data = redis_client.get(cache_key)

    if ceched_data :
        return json.loads(ceched_data)

    users = {
        "username": user.username,
        "role": user.role
    }

    redis_client.set(cache_key, json.dumps(users), ex=60)
    return users


@router.patch("/admin/users/{user_id}/make-admin")
def make_admin(user_id: int, admin: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.role = "admin"
    db.commit()
    return {"message": f"User {user.username} is now admin"}


@router.get("/sessions")
def get_sessions(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.query(RefreshToken).filter(
        RefreshToken.expires_at < datetime.utcnow(),
        RefreshToken.is_revoked == False
    ).update({"is_revoked": True})
    db.commit()
    sessions = db.query(RefreshToken).filter(
        RefreshToken.user_id == user.id,
        RefreshToken.is_revoked == False
    ).all()
    return [{"id": s.id, "device": s.device, "ip": s.ip, "created_at": s.create_at, "expires_at": s.expires_at, "is_revoked": s.is_revoked} for s in sessions]


@router.post("/sessions/logout-all")
def logout_all_sessions(user: User = Depends(get_current_user), current_session_id: int = Depends(get_current_session_id), db: Session = Depends(get_db)):
    sessions = db.query(RefreshToken).filter(
        RefreshToken.user_id == user.id,
        RefreshToken.is_revoked == False
    ).all()
    for s in sessions:
        if s.id != current_session_id:
            s.is_revoked = True
    db.commit()
    return {"message": "Other sessions revoked"}


@router.post("/request-reset")
def request_reset(current_user: User = Depends(get_current_user)):
    reset_token = create_reset_token({"sub": current_user.username})
    return {"reset_token": reset_token}


@router.post("/reset-password")
def reset_password(token: str, new_password: str, db: Session = Depends(get_db)):
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    if payload.get("type") != "reset":
        raise HTTPException(status_code=401, detail="Invalid token type")
    username = payload.get("sub")
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.password = hash_password(new_password)
    db.commit()
    log_action(db, user.id, "reset_password", ip="system")
    return {"message": "Password updated"}

@router.get("/users")
def get_users(
    search: str = None,
    role: str = None,
    sort: str = "asc",
    page: int = 1,
    limit: int = 10,
    db: Session = Depends(get_db)
):
    query = db.query(User)

    if search:
        query = query.filter(User.username.contains(search))

    if role:
        query = query.filter(User.role == role)

    if sort == "asc":
        query = query.order_by(User.id.asc())
    else:
        query = query.order_by(User.id.desc())

    total = query.count()
    users = query.offset((page - 1) * limit).limit(limit).all()

    return {
        "total": total,
        "page": page,
        "limit": limit,
        "users": users
    }

@router.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(
        User.id == user_id,
        User.is_deleted == False
    ).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_deleted = True
    db.commit()

    return {"message": f" , User {user.username} Disabled "}


@router.post("/upload")
def upload_file(file: UploadFile = File(...), user: User = Depends(get_current_user)):
    allowed_types = ["image/jpeg", "image/png" , "application/pdf"]
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="File type is not allowed")
    if file.size > 5 * 1024 * 1024:
        raise HTTPException(status_code=400 , detail="File size is more than 5 MB")

    file_path = f"uploads/{user.id}_{file.filename}"
    with open(file_path, "wb") as buffer :
        shutil.copyfileobj(file.file, buffer)

    return {"message": "File uploaded", "path": file_path}

from backend.models import Task
from backend.services.task_services import create_task, get_tasks, update_task, delete_task

@router.post("/tasks")
def create_task_endpoint(
    title: str,
    description: str = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return create_task(db, user.id, title, description)


@router.get("/tasks")
def get_tasks_endpoint(
    is_done: bool = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return get_tasks(db, user.id, is_done)


@router.patch("/tasks/{task_id}")
def update_task_endpoint(
    task_id: int,
    is_done: bool,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return update_task(db, task_id, user.id, is_done)


@router.delete("/tasks/{task_id}")
def delete_task_endpoint(
    task_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return delete_task(db, task_id, user.id)