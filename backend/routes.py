from http.client import HTTPException
from fastapi import APIRouter
from sqlalchemy.orm import Session
import json
from .core.redis import redis_client
from .models import (User, RefreshToken, AuditLog)
from .permissions import require_permission
from .schemas import (RegisterRequest, SessionResponse, LoginRequest)
from fastapi import (HTTPException, Depends , Request , BackgroundTasks)
from .database import get_db
from .security import (
    get_current_user, get_current_session_id,
    oauth2_scheme , create_reset_token , log_action
)
from datetime import datetime
from .dependencies import get_current_admin
from .tasks import write_log
from slowapi import Limiter
from slowapi.util import get_remote_address
from backend.services.auth_services import (login , register ,
                                            reset_password , refresh_token_endpoint , logout , get_user_sessions)
from fastapi import BackgroundTasks
import random
from celery import Celery
from backend.celery_app import celery
import asyncio
limiter = Limiter(key_func=get_remote_address)

router = APIRouter()

otp = random.randint(
    100000,
    999999
)

@celery.task
def send_email():
    print("email sent ")


@router.post("/login" )
@limiter.limit("5 / minute")
def login_user ( request: Request, data : LoginRequest, db: Session = Depends(get_db)):
    return login(request ,db, data.username,data.password)

@router.post("/register")
def register_user(data: RegisterRequest, background_tasks: BackgroundTasks ,  db: Session = Depends(get_db)):
    background_tasks.add_task(
        send_email
    )
    return register(db, background_tasks , data.username, data.password)

@router.post("/refresh")
def refresh_token_endpoints(refresh_token: str, db: Session = Depends(get_db)):
    return refresh_token_endpoint(db, refresh_token)


@router.get("/logout")
def logouts(
        token : str = Depends(oauth2_scheme),
        user : User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    return logout( db, token , user)


@router.patch("/admin/users/{user_id}/make-admin")
def make_admin(user_id: int, admin: User = Depends(get_current_admin) ,db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id ).first()

    if not user:
        raise HTTPException(status_code=401, detail="user not found")

    user.role = "admin"
    db.commit()

    return {  "message": f"User {user.username} is now admin" }


@router.get("/sessions")
def get_sessions(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.query(RefreshToken).filter(
        RefreshToken.expires_at < datetime.utcnow(),
        RefreshToken.is_revoked == False
    ).update({"is_revoked": True})
    db.commit()

    sessions = db.query(RefreshToken).filter(RefreshToken.user_id == user.id, RefreshToken.is_revoked == False)
    return [
        {
            "id":s.id,
            "device":s.device,
            "ip": s.ip ,
            "create_at": s.create_at,
            "expirse_at":s.expires_at,
            "is_revoked":s.is_revoked
    }
        for s in sessions
    ]

@router.delete("/sessions/{session_id}")
def delete_session(session_id: int, user: User = Depends(get_current_user), db:Session = Depends(get_db)):
    session = db.query(RefreshToken).filter(RefreshToken.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="session not found")
    if session.user_id != user.id and user.role != "admin":
        raise HTTPException(status_code=403, detail="session not allowed")
    session.is_revoked = True
    db.commit()
    return { "message": f"session {session_id} revoked"}

@router.post("/sessions/logout-all")
def logout_all(user: User = Depends(get_current_user),
               current_session_id: int = Depends(get_current_session_id),
               db: Session = Depends(get_db)):
    session = db.query(RefreshToken).filter(RefreshToken.expires_at < datetime.utcnow(), RefreshToken.is_revoked == False).all()
    for s in session:
        if s.id != current_session_id:s.is_revoked = True

    db.commit()
    return {"message": "Other sessions revoked"}

@router.get("/taamrrin")
def sss (user:User = Depends(get_current_user) ,db:Session = Depends(get_db)):
    if not user:
        raise HTTPException(status_code=401, detail= "user not")

    return {
        "username": user.username,
        "yuor": user.role
    }

@router.post("/request-reset")
def request_reset(
    current_user: User = Depends(get_current_user)
):
    reset_token = create_reset_token({
        "sub": current_user.username
    })

    return {
        "reset_token": reset_token
    }

@router.post("/reset-password")
def reset_passwords(
    token: str,
    new_password: str,
    db: Session = Depends(get_db)
):
    return reset_password(db, token, new_password)

@router.get("/logs")
def get_logs(
        db: Session = Depends(get_db),
        admin: User = Depends(get_current_admin)
):
    return db.query(AuditLog).all()
@router.get("/users")
def get_users(
        search : str = None,
        role: str = None,
        sort: str = "asc",
        db : Session = Depends(get_db)
):
    query = db.query(User)

    if search:
        query = query.filter(User.username.contains(search))

    if role:
        query = query.filter(User.role == role)

    if sort:
        query = query.order_by(User.id.desc())

    else:
        query = query.order_by(User.id.asc())

    users = query.all()
    return users

@router.get("/users/{id}")
def delete_user(
        id: int,
        admin: User = Depends(require_permission("delete_user"))
):
    return {"message": "User deleted"}

@router.get("/sessionses", response_model=list[SessionResponse])
def get_sessions(page: int = 1, limit: int = 100 ,
                 device: str | None = None,
                 revoked : bool | None = None ,
                 sort_by: str = "created_at",
                 order: str = "desc",
                 current_user : User = Depends(get_current_user),db : Session = Depends(get_db)):
    return get_user_sessions(
        db,
        current_user,
        page,
        limit,
        device,
        revoked,
        sort_by,
        order

    )

@router.get("/test-redis")
def test_redis():
    redis_client.set(
        "username",
        "sam"
    )
    value = redis_client.get("username")
    return { "value" : value }


@router.get("/userses")
def get_users(db: Session = Depends(get_db)):
    cached_users = redis_client.get("userses")
    if cached_users:
        return json.loads(cached_users)

    users = db.query(User).all()
    users_data = [{"username": u.username, "ip": u.ip} for u in users]
    return users_data

@router.get("/slow")
def slow_endpoint():
    import time
    time.sleep(2)
    return {"message": "done after 2 seconds"}

@router.get("/fast")
def fast_endpoint():
    await asyncio.sleep(2)
    return {"message":"done after 2 seconds"}

@router.get("/soper_fast")
def soper_fast():
    result1, result2 = await asyncio.gather(
        asyncio.sleep(1),
        asyncio.sleep(1)
    )
    return {"message" : "two tasks done in 1 second"}