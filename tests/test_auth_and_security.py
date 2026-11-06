import uuid
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from prism.api.main import app
from prism.security.jwt import (
    create_access_token,
    create_refresh_token,
    create_token,
    decode_token,
)
from prism.security.password import hash_password, verify_password

client = TestClient(app)


def test_password_hashing_and_verification() -> None:
    raw_password = "SecurePassword123!"
    hashed = hash_password(raw_password)

    assert hashed.startswith("pbkdf2_sha256$")
    assert verify_password(raw_password, hashed) is True
    assert verify_password("WrongPassword!", hashed) is False
    assert verify_password(raw_password, "invalid_hash_string") is False
    assert verify_password("", hashed) is False


def test_jwt_token_lifecycle() -> None:
    dev_id = f"dev_jwt_{uuid.uuid4().hex[:6]}"
    access_token = create_access_token(
        dev_id, role="senior_engineer", expires_minutes=15
    )
    refresh_token = create_refresh_token(dev_id, expires_days=7)

    decoded_access = decode_token(access_token, expected_type="access")
    assert decoded_access["sub"] == dev_id
    assert decoded_access["role"] == "senior_engineer"
    assert decoded_access["type"] == "access"

    decoded_refresh = decode_token(refresh_token, expected_type="refresh")
    assert decoded_refresh["sub"] == dev_id
    assert decoded_refresh["type"] == "refresh"

    # Mismatched token types should fail
    with pytest.raises(ValueError, match="Expected token of type 'access'"):
        decode_token(refresh_token, expected_type="access")

    with pytest.raises(ValueError, match="Expected token of type 'refresh'"):
        decode_token(access_token, expected_type="refresh")

    # Expired token
    expired_token = create_token(
        {"sub": dev_id}, timedelta(seconds=-10), token_type="access"
    )
    with pytest.raises(ValueError, match="Token has expired"):
        decode_token(expired_token)

    # Tampered token
    tampered = access_token[:-4] + "xxxx"
    with pytest.raises(ValueError, match="Invalid token signature"):
        decode_token(tampered)


def test_auth_registration_and_login_flow() -> None:
    unique_suffix = uuid.uuid4().hex[:8]
    test_email = f"developer_{unique_suffix}@example.com"
    test_password = "SuperSecretPassword2026!"
    dev_id = f"dev_{unique_suffix}"

    # 1. Register new developer
    reg_res = client.post(
        "/auth/register",
        json={
            "email": test_email,
            "password": test_password,
            "name": f"Test Dev {unique_suffix}",
            "developer_id": dev_id,
            "role": "developer",
        },
    )
    assert reg_res.status_code == 201
    reg_data = reg_res.json()
    assert reg_data["developer_id"] == dev_id
    assert "access_token" in reg_data
    assert "refresh_token" in reg_data

    # 2. Duplicate registration should be rejected
    dup_res = client.post(
        "/auth/register",
        json={
            "email": test_email,
            "password": test_password,
            "name": "Duplicate Dev",
        },
    )
    assert dup_res.status_code == 409
    assert "already exists" in dup_res.json()["detail"]

    # 3. Login with correct credentials
    login_res = client.post(
        "/auth/login",
        json={
            "email": test_email,
            "password": test_password,
        },
    )
    assert login_res.status_code == 200
    login_data = login_res.json()
    assert login_data["developer_id"] == dev_id
    assert login_data["access_token"]
    access_token = login_data["access_token"]
    refresh_token = login_data["refresh_token"]

    # 4. Login with wrong password
    bad_login = client.post(
        "/auth/login",
        json={
            "email": test_email,
            "password": "CompletelyWrongPassword!",
        },
    )
    assert bad_login.status_code == 401
    assert "Invalid email or password" in bad_login.json()["detail"]

    # 5. Access profile via /auth/me with Bearer token
    me_res = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert me_res.status_code == 200
    profile = me_res.json()
    assert profile["developer_id"] == dev_id
    assert profile["email"] == test_email
    assert profile["is_active"] is True

    # 6. Access profile without token
    unauth_res = client.get("/auth/me")
    assert unauth_res.status_code == 401

    # 7. Refresh access token
    refresh_res = client.post(
        "/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refresh_res.status_code == 200
    refreshed_data = refresh_res.json()
    assert refreshed_data["access_token"]
    assert refreshed_data["developer_id"] == dev_id

    # 8. Refresh with invalid token
    bad_refresh = client.post(
        "/auth/refresh",
        json={"refresh_token": "malformed.invalid.token"},
    )
    assert bad_refresh.status_code == 401

    # 9. Logout
    logout_res = client.post(
        "/auth/logout",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert logout_res.status_code == 200
    assert logout_res.json()["status"] == "logged_out"
