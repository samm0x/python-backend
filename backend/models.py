
from sqlalchemy import Column, Integer, String , ForeignKey, DateTime,Boolean
from sqlalchemy.orm import relationship
from datetime import  datetime
from .database import Base


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column (String, unique=True, index=True)
    password = Column (String)
    role = Column(String, default="user")
    is_deleted = Column(Boolean, default=False)
    refresh_tokens= relationship("RefreshToken", back_populates="user")

class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column (Integer, ForeignKey("users.id"))
    devici_info = Column (String)
    token = Column (String, nullable=False)
    expires_at = Column (DateTime, nullable=False)
    create_at = Column (DateTime, default=datetime.utcnow)
    is_revoked = Column (Boolean, default=False)
    device = Column(String, nullable=True)
    ip = Column(String, nullable=True)
    user = relationship("User", back_populates="refresh_tokens")

class TokenBlacklist(Base):
    __tablename__= "token_blacklist"
    id = Column(Integer, primary_key=True )
    token = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class PasswordResetToken(Base):
    __tablename__ = "password_reset_token"
    id = Column(Integer, primary_key=True)
    token = Column (String, unique=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    is_used = Column(Boolean, default= False)
    expires_at =Column(DateTime)
    user = relationship("User")


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer)
    action = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

