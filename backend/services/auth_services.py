
from http.client import HTTPException
from sqlalchemy.orm import Session
from backend.config import SECRET_KEY, ALGORITHM
from backend.models import (User, RefreshToken, TokenBlacklist)
from fastapi import (HTTPException, Depends ,
                     Request )
from backend.database import get_db
from backend.security import (
    verify_password,
    create_access_token,
    get_current_user,
    hash_password, create_refresh_token,
    hash_refresh_token, log_action
)
from datetime import datetime, timedelta
from jose import jwt
from slowapi import Limiter
from slowapi.util import get_remote_address
from backend.repositories.user_repository import get_user_by_username , create_user , get_user_sessions_query , filter_by_device
from backend.utils.responses import success_response
from fastapi import  BackgroundTasks

limiter = Limiter(key_func=get_remote_address)


def login( request: Request , db : Session , username: str , password: str):


    user = get_user_by_username(db, username)

    user_agent = request.headers.get("User-Agent")
    ip = request.client.host
    if not user:
        raise success_response(message="User not found" , data= login)
    if not verify_password(password, user.password):
        raise success_response(message = "wrong password" , data= login)

    refresh_token = create_refresh_token()

    hashed_refresh = hash_refresh_token(refresh_token)
    refresh_obj = RefreshToken(
        token=hashed_refresh,
        user_id=user.id,
        expires_at=datetime.utcnow() + timedelta(days=7),
        device = user_agent,
        ip=ip
    )
    db.add(refresh_obj)
    db.commit()
    db.refresh(refresh_obj)
    access = create_access_token({
        "sub": user.username,
        "session_id": refresh_obj.id
    })
    log_action(db, user.id , "login", ip)
    return{
        "access_token":access,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }

def register(db: Session ,background_tasks: BackgroundTasks , username: str , password: str):

    # 1. چک یوزر تکراری
    existing_user = get_user_by_username(db, username)


    if existing_user:
        raise HTTPException( status_code=400, detail="User already exists")


    hashed_password = hash_password(password)

    create_user(db, username, hashed_password)

    background_tasks.add_task(
        username
    )


    return {"message": "User registered successfully"}

def reset_password(
    token: str,
    new_password: str,
    db: Session = Depends(get_db)
):
    payload = jwt.decode(
        token,
        SECRET_KEY,
        algorithms=[ALGORITHM]
    )

    # چک نوع توکن
    if payload.get("type") != "reset":
        raise HTTPException(
            status_code=401,
            detail="Invalid token type"
        )

    username = payload.get("sub")

    user = get_user_by_username(db, username)

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    user.password = hash_password(new_password)
    db.commit()

    log_action(db, user.id , "reset_password" )

    return {
        "message": "Password updated"
    }

def refresh_token_endpoint(db: Session, refresh_token : str ):

    # 🔥 cleanup
    db.query(RefreshToken).filter(RefreshToken.expires_at < datetime.utcnow(), RefreshToken.is_revoked == False).update({"is_revoked": True})
    db.commit()

    # 🔥 reuse attack detection (اولین چیز!)
    tokens = db.query(RefreshToken).all()

    for t in tokens:
        if verify_password(refresh_token, t.token):
            if t.is_revoked:
                db.query(RefreshToken).filter(
                    RefreshToken.user_id == t.user_id
                ).update({"is_revoked": True})

                db.commit()

                raise HTTPException(
                    status_code=401,
                    detail="Token reuse detected. All sessions revoked"
                )

    # 🔐 حالا چک معتبر بودن
    hashed_refresh = hash_refresh_token(refresh_token)

    valid_token = db.query(RefreshToken).filter(
        RefreshToken.token == hashed_refresh,
        RefreshToken.is_revoked == False
    ).first()

    if not valid_token:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    if valid_token.expires_at < datetime.utcnow():
        raise HTTPException(status_code=401, detail="Refresh token expired")

    # 🔄 revoke قبلی
    valid_token.is_revoked = True

    user = valid_token.user
    new_access = create_access_token({"sub": user.username})

    # 🔄 ساخت refresh جدید
    new_refresh = create_refresh_token()
    hashed_new_refresh = hash_refresh_token(new_refresh)

    new_refresh_obj = RefreshToken(
        token=hashed_new_refresh,
        user_id=user.id,
        expires_at=datetime.utcnow() + timedelta(days=7)
    )

    db.add(new_refresh_obj)
    db.commit()

    return {
        "access_token": new_access,
        "refresh_token": new_refresh
    }

def logout(
        db: Session ,
        session_id: int ,
        current_user: User ,
        token: str
):
    blacklisted_token = TokenBlacklist(token=token)

    (db.query(RefreshToken).
     filter(RefreshToken.expires_at < datetime.utcnow(),
            RefreshToken.is_revoked == False).update({"is_revoked": True }))

    session = (db.query(RefreshToken).
     filter(RefreshToken.user_id == session_id
            , RefreshToken.is_revoked == False).update({"is_revoked": True }))
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not allowed")

    db.add(blacklisted_token)
    db.commit()
    return {"message": "Logout out from all devices"}




def get_user_sessions(sort_by: str , order: str , page: int = 1, limit: int = 10 ,
                 device: str | None = None,
                 revoked : bool | None = None ,
                 current_user : User = Depends(get_current_user),db : Session = Depends(get_db)):
    query = get_user_sessions_query(db, current_user.id)
    allowed_sort_fields = {
        "created_at": RefreshToken.created_at,
        "expires_at": RefreshToken.expires_at,
        "ip": RefreshToken.ip
    }
    sort_column = allowed_sort_fields.get(sort_by, RefreshToken.created_at)
    if order == "asc":
        query = query.order_by(sort_column.asc())
    else:
        query = query.order_by(sort_column.desc())

    if device:
        query = filter_by_device(query , device)
    if revoked:
        query = query.filter(RefreshToken.revoked == revoked)

    offset = (page - 1) * limit

    sessions = query.offset(offset).limit(limit).all()
    return [
        {
            "id": s.id,
            "device":s.device,
            "ip": s.ip,
            "is_revoked": s.is_revoked,
            "sort_by": sort_column
        }
        for s in sessions
    ]

