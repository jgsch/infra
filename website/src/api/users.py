from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from config import admin_secret_key
from db import User, get_database
from utils import hash_password

router = APIRouter(prefix="/users", tags=["Users"])


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)
    admin_password: str = Field(...)
    overwrite: bool | None = Field(None)


@router.post("")
def register_user(user: UserCreate, db: Session = Depends(get_database)):
    if user.admin_password != admin_secret_key:
        raise HTTPException(status_code=403, detail="Invalid admin password")

    db_user = db.query(User).filter(User.username == user.username).first()
    if db_user:
        if user.overwrite:
            db.delete(db_user)
            db.commit()
        else:
            raise HTTPException(status_code=409, detail="Username already registered")

    new_user = User(
        username=user.username,
        hashed_password=hash_password(user.password),
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    print(f"New user ('{new_user.username}') added!")


class UserDelete(BaseModel):
    username: str = Field(..., description="Username of the user to delete")
    admin_password: str = Field(..., description="Admin password to authorize deletion")


@router.delete("")
def delete_user(user: UserDelete, db: Session = Depends(get_database)):
    if user.admin_password != admin_secret_key:
        raise HTTPException(status_code=403, detail="Invalid admin password")

    db_user = db.query(User).filter(User.username == user.username).first()
    if db_user is None:
        raise HTTPException(status_code=404, detail="Username not found")

    db.delete(db_user)
    db.commit()
