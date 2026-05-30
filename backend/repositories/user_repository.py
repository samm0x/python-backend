from sqlalchemy.orm import Session
from backend.models import User , RefreshToken

def get_user_by_username(db:Session, username: str ):
    return db.query(User).filter(User.username == username).first()

def get_user_by_id(db:Session, user_id: int):
    return db.query(User).filter(User.id == user_id).first()

def create_user(db:Session, username: str , hashed_password: str):
    user = User(username=username, password=hashed_password , role= "user")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_user_sessions_query(db: Session, user_id: int):
    return db.query(RefreshToken).filter(RefreshToken.user_id == user_id)

def filter_by_device(query  , device: str ):
    return query.filter(RefreshToken.device.ilike(f"%{device}%"))