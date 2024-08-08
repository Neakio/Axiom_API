# ------------------------------ PACKAGES ------------------------------
# General packages
from pydantic import BaseModel, EmailStr
from typing import Optional


# --------------------------- PYDANTIC MODELS ---------------------------
class UserBase(BaseModel):
    surname: Optional[str] = None
    firstname: Optional[str] = None
    email: Optional[EmailStr] = None


class UserCreate(UserBase):
    email: EmailStr
    password: str


class UserUpdate(UserBase):
    pass


class UserInDB(UserBase):
    id: int
    hashed_password: str
    disabled: bool

    class Config:
        orm_mode = True


class User(UserInDB):
    pass


class UserPasswordChange(BaseModel):
    old_password: str
    new_password: str


class UserPasswordReset(BaseModel):
    email: EmailStr


class UserFilter(BaseModel):
    surname: Optional[str] = None
    firstname: Optional[str] = None
    email: Optional[EmailStr] = None


class UserChangeStatus(BaseModel):
    email: EmailStr
