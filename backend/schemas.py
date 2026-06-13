from pydantic import BaseModel
from datetime import datetime
class LoginRequest(BaseModel):
    username: str
    password: str

class RegisterRequest(BaseModel):
    email: str
    username: str
    password: str


class LogoutRequest(BaseModel):
    refresh_token: str

class UserRequest(BaseModel):
    id: int
    username: str
    role: str
    class Config:
        from_attributes = True

class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str


class SessionResponse(BaseModel):
    id: int
    device: str
    ip: int
    is_revoked: bool
    created_at: datetime
    expires_at: datetime



