
import secrets
from datetime import datetime, timedelta
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordBearer
from fastapi import Depends
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from fastapi import HTTPException , Request
from .models import User, TokenBlacklist , AuditLog
from backend.config import settings
from .database import get_db
import hashlib
from time import time

SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_refresh_token(token: str) :
    return hashlib.sha256(token.encode()).hexdigest()


def hash_password(password: str):
    return pwd_context.hash(password)

def verify_password(plain, hashed):
    return pwd_context.verify(plain, hashed)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


oauth2_scheme = OAuth2PasswordBearer(tokenUrl = "login")

def get_current_user( token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    blacklist = db.query(TokenBlacklist).filter(TokenBlacklist.token == token).first()
    if blacklist :
        raise HTTPException(status_code=401, detail="Token revoked")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        session_id = payload.get("session_id")
        if username is None:
            raise HTTPException(status_code=401, detail="User not found")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.query(User).filter(User.username == username).first()

    if user is None:
        raise HTTPException( status_code= 401,
            detail = "User not found"
        )

    return user


def create_refresh_token():
    return secrets.token_urlsafe(32)


def get_current_session_id(token: str = Depends(oauth2_scheme)):
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    session_id = payload.get("session_id")

    if session_id is None:
        raise HTTPException(status_code= 401,
            detail = "Invalid token"
        )
    return session_id


def create_reset_token(data: dict):
    to_encode = data.copy()
    expires = datetime.utcnow() + timedelta(minutes= 15)
    to_encode.update({"exp": expires , "type": "reset"})
    return jwt.encode(to_encode, SECRET_KEY , algorithm= ALGORITHM)


requests_memory  = {}
def rate_limited(max_requests: int , seconds: int ):
    def checker(request: Request):
        ip = request.client.host
        now = time()
        if ip not in requests_memory:
            requests_memory[ip] = []

        requests_memory[ip] = [
            t for t in requests_memory[ip]
            if now - t < seconds
        ]

        if len (requests_memory[ip]) >= max_requests :
            raise HTTPException(status_code=429, detail="Too many requests")
        requests_memory[ip].append(now)

    return checker

def log_action ( db , user_id , action , ip ):
    log = AuditLog(
        user_id=user_id,
        action=action,
        ip=ip
    )
    db.add(log)
    db.commit()