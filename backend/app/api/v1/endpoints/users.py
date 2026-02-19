from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from pydantic import BaseModel, EmailStr
import uuid

from app.api.v1.endpoints.auth import get_current_active_superuser, get_current_active_user
from app.db.session import get_db
from app.models.models import User
from app.core.security import hash_password

router = APIRouter()

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    full_name: str | None = None
    password: str
    role: str = "viewer"

class UserUpdate(BaseModel):
    full_name: str | None = None
    role: str | None = None
    password: str | None = None
    is_active: bool | None = None

class UserOut(BaseModel):
    id: uuid.UUID
    username: str
    email: EmailStr
    full_name: str | None = None
    role: str
    is_active: bool

    class Config:
        from_attributes = True


@router.get("/", response_model=List[UserOut], dependencies=[Depends(get_current_active_superuser)])
async def list_users(
    skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)
):
    """
    List all users (Admin only).
    """
    query = select(User).offset(skip).limit(limit)
    result = await db.execute(query)
    users = result.scalars().all()
    return users


@router.post("/", response_model=UserOut, status_code=status.HTTP_201_CREATED, dependencies=[Depends(get_current_active_superuser)])
async def create_user(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    """
    Create a new user (Admin only).
    """
    query = select(User).where((User.username == user_in.username) | (User.email == user_in.email))
    result = await db.execute(query)
    existing_user = result.scalars().first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this username or email already exists",
        )

    new_user = User(
        id=uuid.uuid4(),
        username=user_in.username,
        email=user_in.email,
        full_name=user_in.full_name,
        hashed_password=hash_password(user_in.password),
        role=user_in.role,
        is_active=True,
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user


@router.get("/me", response_model=UserOut)
async def read_current_user(current_user: User = Depends(get_current_active_user)):
    """
    Get current user profile.
    """
    return current_user


@router.put("/{user_id}", response_model=UserOut, dependencies=[Depends(get_current_active_superuser)])
async def update_user(
    user_id: uuid.UUID, user_update: UserUpdate, db: AsyncSession = Depends(get_db)
):
    """
    Update a user (Admin only).
    """
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user_update.full_name is not None:
        user.full_name = user_update.full_name
    if user_update.role is not None:
        user.role = user_update.role
    if user_update.is_active is not None:
        user.is_active = user_update.is_active
    if user_update.password:
        user.hashed_password = hash_password(user_update.password)

    await db.commit()
    await db.refresh(user)
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(get_current_active_superuser)])
async def delete_user(user_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """
    Delete a user (Admin only).
    """
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    await db.delete(user)
    await db.commit()
