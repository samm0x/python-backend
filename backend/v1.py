from http.client import HTTPException
from fastapi import APIRouter
from sqlalchemy.orm import Session

from .config import SECRET_KEY, ALGORITHM

from .models import (User, RefreshToken, TokenBlacklist, AuditLog)
from fastapi.security import OAuth2PasswordRequestForm

from .permissions import require_permission
from backend.repositories.user_repository import get_user_by_username
from .schemas import (RegisterRequest,
                      UserRequest, LoginResponse)
from fastapi import (HTTPException, Depends ,
                     Request , BackgroundTasks)
from .database import get_db
from .security import (
    verify_password,
    create_access_token,
    get_current_user,
    hash_password, create_refresh_token,
    hash_refresh_token, get_current_session_id,
    oauth2_scheme , create_reset_token , log_action
)
from datetime import datetime, timedelta
from .dependencies import get_current_admin
from jose import jwt
from .tasks import write_log
from slowapi import Limiter
from slowapi.util import get_remote_address

from backend.services.auth_services import login


limiter = Limiter(key_func=get_remote_address)

router = APIRouter()




@router.post("/login" ,response_model=LoginResponse)
@limiter.limit("5 / minute")
def logins ( request: Request, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    return login(db, form_data.username,form_data.password)

@router.post("/register")
def register(data: RegisterRequest, db: Session = Depends(get_db)):

    # 1. چک یوزر تکراری
    existing_user = db.query(User).filter(User.username == data.username).first()


    if existing_user:
        raise HTTPException( status_code=400, detail="User already exists")


    hashed_password = hash_password(data.password)

    user = User(
        username=data.username,
        password=hashed_password,
        role = "user"
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return {"message": "User registered successfully"}

@router.post("/refresh")
def refresh_token_endpoint(refresh_token: str, db: Session = Depends(get_db)):

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

@router.get("/logout")
def logout(
        token : str = Depends(oauth2_scheme),
        user : User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    blacklisted_token = TokenBlacklist(token=token)

    db.query(RefreshToken).filter(RefreshToken.expires_at < datetime.utcnow(), RefreshToken.is_revoked == False)(db,user ).update({"is_revoked": True })

    db.query(RefreshToken).filter(RefreshToken.user_id == user.id, RefreshToken.is_revoked == False).update({"is_revoked": True })

    db.add(blacklisted_token)
    db.commit()
    return {"message": "Logout out from all devices"}



@router.get("/me", response_model=UserRequest)
def get_me (user: User = Depends(get_current_user)):
    return user


@router.get("/profile")
def profile (request: Request , user: User = Depends(get_current_user)):
    client_id = request.client.host
    user_agent = request.headers.get("User-Agent")

    if not user:
        raise HTTPException(status_code=401, detail= "user not")
    return {
        "username": user.username,
        "role": user.role,
        "client_id": client_id,
        "user_agent": user_agent
    }

@router.get("/users")
def users( db: Session = Depends(get_db)):
    return db.query(User).all()


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
               current_session_id: int = Depends(get_current_session_id) ,
               db: Session = Depends(get_db)):
    session = db.query(RefreshToken).filter(RefreshToken.expires_at < datetime.utcnow(), RefreshToken.is_revoked == False)(db , user).all()
    for s in session:
        if s.id != current_session_id:s.is_revoked = True

    db.commit()
    return {"message": "Other sessions revoked"}
#
# @router.get("/tamrin")
# def tamrin (  user: User , admin:User = Depends(get_current_admin), db:Session = Depends(get_db)):
#     admin = db.query(User).filter(User.username == admin.username).first()
#     log_action(db, admin.id , f"delete_user_{user.id}")
#     return {
#         "username": admin.username,
#         "to hasti": admin.role
#     }

@router.get("/taamrrin")
def sss (user:User = Depends(get_current_user) ,db:Session = Depends(get_db)):
    if not user:
        raise HTTPException(status_code=401, detail= "user not")

    return {
        "username": user.username,
        "yuor": user.role
    }

@router.post("/logout-all")
def logout_all(user: User = Depends(get_current_user), db :Session = Depends(get_db)):
    sessions = db.query(RefreshToken).filter(RefreshToken.user_id == user.id, RefreshToken.is_revoked == False)
    for session in sessions:
        session.is_revoked = True

    db.commit()

    log_action(
        db, user.id ,
        "logout_all_devices"

    )
    return { "message": "logout out from all devices"}

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

    user = db.query(User).filter(
        User.username == username
    ).first()

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

@router.get("/logs")
def get_logs(
        db: Session = Depends(get_db),
        admin: User = Depends(get_current_admin)
):
    return db.query(AuditLog).all

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

@router.post("/login")
def login (background_tasks: BackgroundTasks):
    background_tasks.add_task(write_log, "sam")
    return { "message": "Logged in "}