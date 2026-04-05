from uuid import UUID
from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    display_name: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: UUID
    email: str
    display_name: str | None
    role: str
    preferences: dict

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    display_name: str | None = None
    preferences: dict | None = None
