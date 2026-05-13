"""
auth/router.py
==============
/auth/register  — create new business account
/auth/login     — get JWT token
/auth/me        — get current user profile
/auth/update    — update business name or password
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, field_validator
from typing import Optional
from sqlalchemy.orm import Session

from app.models.database import get_db, User
from app.auth.core import (
    hash_password, verify_password,
    create_access_token, get_current_user
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ── Schemas ────────────────────────────────────────────────────────────────────
class RegisterRequest(BaseModel):
    email: str
    business_name: str
    password: str

    @field_validator("password")
    @classmethod
    def password_strength(cls, v):
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters")
        return v

    @field_validator("email")
    @classmethod
    def email_lower(cls, v):
        return v.lower().strip()


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    email: str
    business_name: str
    plan: str


class UpdateRequest(BaseModel):
    business_name: Optional[str] = None
    current_password: Optional[str] = None
    new_password: Optional[str] = None


# ── Endpoints ──────────────────────────────────────────────────────────────────
@router.post("/register", response_model=LoginResponse, status_code=201)
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    """Create a new business account and return a JWT immediately."""
    # Check duplicate email
    if db.query(User).filter(User.email == req.email).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists"
        )
    user = User(
        email=req.email,
        business_name=req.business_name.strip(),
        hashed_password=hash_password(req.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(user.id, user.email)
    return LoginResponse(
        access_token=token,
        user_id=user.id,
        email=user.email,
        business_name=user.business_name,
        plan=user.plan,
    )


@router.post("/login", response_model=LoginResponse)
def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    Standard OAuth2 login — accepts form data (username = email, password).
    Returns JWT token valid for 7 days.
    """
    user = db.query(User).filter(User.email == form.username.lower()).first()
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated"
        )

    token = create_access_token(user.id, user.email)
    return LoginResponse(
        access_token=token,
        user_id=user.id,
        email=user.email,
        business_name=user.business_name,
        plan=user.plan,
    )


@router.get("/me")
def get_profile(current_user: User = Depends(get_current_user)):
    """Return current logged-in user's profile."""
    return {
        "user_id": current_user.id,
        "email": current_user.email,
        "business_name": current_user.business_name,
        "plan": current_user.plan,
        "member_since": current_user.created_at.strftime("%Y-%m-%d"),
    }


@router.put("/update")
def update_profile(
    req: UpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update business name or change password."""
    if req.business_name:
        current_user.business_name = req.business_name.strip()

    if req.new_password:
        if not req.current_password:
            raise HTTPException(status_code=400, detail="current_password required")
        if not verify_password(req.current_password, current_user.hashed_password):
            raise HTTPException(status_code=401, detail="Current password is incorrect")
        if len(req.new_password) < 6:
            raise HTTPException(status_code=400, detail="New password must be at least 6 characters")
        current_user.hashed_password = hash_password(req.new_password)

    db.commit()
    return {"message": "Profile updated successfully"}


@router.delete("/account")
def delete_account(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Permanently delete account and ALL associated data."""
    db.delete(current_user)
    db.commit()
    return {"message": "Account and all data deleted permanently"}