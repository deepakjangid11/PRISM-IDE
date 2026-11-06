from collections.abc import Callable
from typing import Any

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from prism.api.dependencies import developer_repo
from prism.security.jwt import decode_token

security_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Security(security_bearer),
) -> dict[str, Any]:
    """Extract and validate the current authenticated developer from Bearer token."""
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        claims = decode_token(credentials.credentials, expected_type="access")
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(err),
            headers={"WWW-Authenticate": "Bearer"},
        ) from err

    developer_id = claims.get("sub")
    if not developer_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing subject identifier",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = developer_repo.get_developer(developer_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated user no longer exists",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def get_current_active_user(
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Ensure the authenticated user is marked active."""
    if not current_user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated",
        )
    return current_user


async def get_optional_current_user(
    credentials: HTTPAuthorizationCredentials | None = Security(security_bearer),
) -> dict[str, Any] | None:
    """Extract authenticated user if Bearer token is provided; return None if unauthenticated."""
    if credentials is None or not credentials.credentials:
        return None

    try:
        claims = decode_token(credentials.credentials, expected_type="access")
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(err),
            headers={"WWW-Authenticate": "Bearer"},
        ) from err

    developer_id = claims.get("sub")
    if not developer_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing subject identifier",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = developer_repo.get_developer(developer_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated user no longer exists",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated",
        )

    return user


def verify_developer_ownership(
    target_developer_id: str,
    current_user: dict[str, Any] | None,
) -> None:
    """Enforce that authenticated user matches the resource owner or has admin privileges."""
    if current_user is None:
        return

    token_dev_id = str(current_user.get("developer_id", "")).strip()
    target_clean = str(target_developer_id).strip()
    role = current_user.get("role", "developer")

    if (
        token_dev_id
        and target_clean
        and token_dev_id != target_clean
        and role != "admin"
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: You cannot access or modify resources belonging to another developer",
        )


def require_role(allowed_roles: list[str]) -> Callable[..., Any]:
    """Dependency factory enforcing role-based authorization."""

    async def role_checker(
        current_user: dict[str, Any] = Depends(get_current_active_user),
    ) -> dict[str, Any]:
        user_role = current_user.get("role", "developer")
        if user_role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: Requires role in {allowed_roles}",
            )
        return current_user

    return role_checker
