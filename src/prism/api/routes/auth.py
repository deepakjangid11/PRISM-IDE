import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, Field, field_validator

from prism.api.dependencies import developer_repo
from prism.logging.logger import get_logger
from prism.security.dependencies import get_current_active_user, security_bearer
from prism.security.jwt import (
    create_access_token,
    create_refresh_token,
    decode_token,
    revoke_token,
)
from prism.security.password import hash_password, verify_password

logger = get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


class RegisterRequest(BaseModel):
    email: str = Field(
        ..., min_length=3, max_length=254, description="User email address"
    )
    password: str = Field(..., min_length=8, description="Minimum 8 characters")
    name: str = Field(..., min_length=1)
    developer_id: str | None = None
    role: str = "developer"

    @field_validator("email")
    @classmethod
    def validate_email_format(cls, v: str) -> str:
        clean = v.strip().lower()
        if "@" not in clean or "." not in clean.split("@")[-1]:
            raise ValueError("Invalid email address format")
        return clean


class LoginRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=254)
    password: str

    @field_validator("email")
    @classmethod
    def validate_email_format(cls, v: str) -> str:
        clean = v.strip().lower()
        if "@" not in clean or "." not in clean.split("@")[-1]:
            raise ValueError("Invalid email address format")
        return clean


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    developer_id: str
    role: str


class UserProfileResponse(BaseModel):
    developer_id: str
    name: str | None
    email: str | None
    role: str
    is_active: bool


@router.post(
    "/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED
)
async def register(request: RegisterRequest) -> TokenResponse:
    """Register a new developer account and return initial JWT tokens."""
    cleaned_email = request.email.strip().lower()
    existing = developer_repo.get_by_email(cleaned_email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"An account with email '{cleaned_email}' already exists",
        )

    developer_id = request.developer_id or f"dev_{uuid.uuid4().hex[:12]}"
    if developer_repo.get_developer(developer_id):
        developer_id = f"dev_{uuid.uuid4().hex[:12]}"

    pwd_hash = hash_password(request.password)

    try:
        user = developer_repo.create_user(
            developer_id=developer_id,
            email=cleaned_email,
            password_hash=pwd_hash,
            name=request.name.strip(),
            role=request.role.strip() if request.role else "developer",
        )
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(err)
        ) from err

    access_token = create_access_token(
        developer_id=developer_id, role=user.get("role", "developer")
    )
    refresh_token = create_refresh_token(developer_id=developer_id)

    logger.info("Registered new developer '%s' (%s)", developer_id, cleaned_email)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        developer_id=developer_id,
        role=user.get("role", "developer"),
    )


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest) -> TokenResponse:
    """Authenticate with email and password to receive JWT tokens."""
    cleaned_email = request.email.strip().lower()
    user = developer_repo.get_by_email(cleaned_email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    stored_hash = user.get("password_hash")
    if not stored_hash or not verify_password(request.password, stored_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account has been deactivated",
        )

    developer_id = user["developer_id"]
    role = user.get("role", "developer")

    access_token = create_access_token(developer_id=developer_id, role=role)
    refresh_token = create_refresh_token(developer_id=developer_id)

    logger.info("Developer '%s' authenticated successfully", developer_id)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        developer_id=developer_id,
        role=role,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(request: RefreshTokenRequest) -> TokenResponse:
    """Exchange a valid refresh token for a new access token."""
    try:
        claims = decode_token(request.refresh_token, expected_type="refresh")
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=str(err)
        ) from err

    developer_id = claims.get("sub")
    if not developer_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing subject identifier",
        )

    user = developer_repo.get_developer(developer_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User no longer exists",
        )

    if not user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account has been deactivated",
        )

    role = user.get("role", "developer")
    new_access = create_access_token(developer_id=developer_id, role=role)
    new_refresh = create_refresh_token(developer_id=developer_id)

    return TokenResponse(
        access_token=new_access,
        refresh_token=new_refresh,
        token_type="bearer",
        developer_id=developer_id,
        role=role,
    )


@router.post("/logout")
async def logout(
    current_user: dict[str, Any] = Depends(get_current_active_user),
    credentials: HTTPAuthorizationCredentials | None = Security(security_bearer),
) -> dict[str, str]:
    """Logout current user session and revoke token."""
    if credentials and credentials.credentials:
        revoke_token(credentials.credentials)
    logger.info("Developer '%s' logged out", current_user["developer_id"])
    return {"status": "logged_out", "developer_id": current_user["developer_id"]}


@router.get("/me", response_model=UserProfileResponse)
async def get_current_profile(
    current_user: dict[str, Any] = Depends(get_current_active_user),
) -> UserProfileResponse:
    """Retrieve profile and authentication status of the currently authenticated developer."""
    return UserProfileResponse(
        developer_id=current_user["developer_id"],
        name=current_user.get("name"),
        email=current_user.get("email"),
        role=current_user.get("role", "developer"),
        is_active=bool(current_user.get("is_active", True)),
    )
