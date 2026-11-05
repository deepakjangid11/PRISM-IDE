from datetime import datetime

import pytest
from pydantic import ValidationError

from prism.intelligence.developer_identity import DeveloperIdentityService
from prism.intelligence.models.developer_identity_models import (
    DeveloperIdentificationRequest,
    DeveloperRegistrationRequest,
    DeveloperUpdateRequest,
)
from prism.storage.repositories.memory_repo import InMemoryDeveloperRepository


@pytest.fixture
def identity_service() -> DeveloperIdentityService:
    repo = InMemoryDeveloperRepository()
    return DeveloperIdentityService(developer_repo=repo)


def test_developer_registration_auto_id(
    identity_service: DeveloperIdentityService,
) -> None:
    req = DeveloperRegistrationRequest(name="Alice Dev", email="alice@prism.io")
    profile = identity_service.register_developer(req)

    assert profile.developer_id.startswith("dev_")
    assert profile.name == "Alice Dev"
    assert profile.email == "alice@prism.io"
    assert isinstance(profile.created_at, datetime)
    assert isinstance(profile.updated_at, datetime)


def test_developer_registration_custom_id(
    identity_service: DeveloperIdentityService,
) -> None:
    req = DeveloperRegistrationRequest(
        developer_id="dev_custom_123",
        name="Bob Builder",
        email="bob@prism.io",
    )
    profile = identity_service.register_developer(req)

    assert profile.developer_id == "dev_custom_123"
    assert profile.name == "Bob Builder"
    assert profile.email == "bob@prism.io"


def test_developer_registration_rejects_duplicate_id(
    identity_service: DeveloperIdentityService,
) -> None:
    req1 = DeveloperRegistrationRequest(
        developer_id="dev_dup_id", name="Dev One", email="dev1@prism.io"
    )
    identity_service.register_developer(req1)

    req2 = DeveloperRegistrationRequest(
        developer_id="dev_dup_id", name="Dev Two", email="dev2@prism.io"
    )
    with pytest.raises(ValueError, match="already exists"):
        identity_service.register_developer(req2)


def test_developer_registration_rejects_duplicate_email(
    identity_service: DeveloperIdentityService,
) -> None:
    req1 = DeveloperRegistrationRequest(
        developer_id="dev_email_1", name="Dev One", email="unique@prism.io"
    )
    identity_service.register_developer(req1)

    req2 = DeveloperRegistrationRequest(
        developer_id="dev_email_2", name="Dev Two", email="unique@prism.io"
    )
    with pytest.raises(ValueError, match="already exists"):
        identity_service.register_developer(req2)


def test_developer_registration_invalid_email(
    identity_service: DeveloperIdentityService,
) -> None:
    req = DeveloperRegistrationRequest(name="Bad Email Dev", email="not-an-email")
    with pytest.raises(ValueError, match="Invalid email address format"):
        identity_service.register_developer(req)


def test_developer_registration_schema_rejects_unsupported_fields() -> None:
    with pytest.raises(ValidationError) as exc_info:
        DeveloperRegistrationRequest(
            name="Deepak Jangid",
            email="deepak.phase16@prism.test",
            experience_level="intermediate",  # type: ignore[call-arg]
            primary_role="AI Developer",  # type: ignore[call-arg]
        )
    errors = exc_info.value.errors()
    locs = [e["loc"][0] for e in errors]
    types = [e["type"] for e in errors]
    assert "experience_level" in locs
    assert "primary_role" in locs
    assert all(t == "extra_forbidden" for t in types)


def test_developer_identification_by_id(
    identity_service: DeveloperIdentityService,
) -> None:
    reg = identity_service.register_developer(
        DeveloperRegistrationRequest(
            developer_id="dev_ident_1",
            name="Ident Dev",
            email="ident@prism.io",
        )
    )

    resolved = identity_service.identify_developer(
        DeveloperIdentificationRequest(developer_id="dev_ident_1")
    )
    assert resolved is not None
    assert resolved.developer_id == reg.developer_id
    assert resolved.email == "ident@prism.io"


def test_developer_identification_by_email(
    identity_service: DeveloperIdentityService,
) -> None:
    reg = identity_service.register_developer(
        DeveloperRegistrationRequest(
            developer_id="dev_ident_email",
            name="Email Ident",
            email="findme@prism.io",
        )
    )

    resolved = identity_service.identify_developer(
        DeveloperIdentificationRequest(email="findme@prism.io")
    )
    assert resolved is not None
    assert resolved.developer_id == reg.developer_id
    assert resolved.name == "Email Ident"


def test_developer_identification_not_found(
    identity_service: DeveloperIdentityService,
) -> None:
    resolved = identity_service.identify_developer(
        DeveloperIdentificationRequest(developer_id="dev_nonexistent")
    )
    assert resolved is None


def test_developer_identification_empty_request(
    identity_service: DeveloperIdentityService,
) -> None:
    with pytest.raises(
        ValueError, match="Either developer_id or email must be provided"
    ):
        identity_service.identify_developer(DeveloperIdentificationRequest())


def test_get_developer_profile_success_and_not_found(
    identity_service: DeveloperIdentityService,
) -> None:
    identity_service.register_developer(
        DeveloperRegistrationRequest(
            developer_id="dev_profile_test",
            name="Profile Tester",
            email="tester@prism.io",
        )
    )

    profile = identity_service.get_profile("dev_profile_test")
    assert profile.name == "Profile Tester"

    with pytest.raises(ValueError, match="Developer not found"):
        identity_service.get_profile("dev_does_not_exist")


def test_update_developer_profile(
    identity_service: DeveloperIdentityService,
) -> None:
    identity_service.register_developer(
        DeveloperRegistrationRequest(
            developer_id="dev_upd",
            name="Original Name",
            email="orig@prism.io",
        )
    )

    updated = identity_service.update_profile(
        "dev_upd",
        DeveloperUpdateRequest(name="Updated Name", email="updated@prism.io"),
    )
    assert updated.name == "Updated Name"
    assert updated.email == "updated@prism.io"

    fetched = identity_service.get_profile("dev_upd")
    assert fetched.name == "Updated Name"
    assert fetched.email == "updated@prism.io"


def test_update_developer_profile_rejects_duplicate_email(
    identity_service: DeveloperIdentityService,
) -> None:
    identity_service.register_developer(
        DeveloperRegistrationRequest(developer_id="dev_user_1", email="user1@prism.io")
    )
    identity_service.register_developer(
        DeveloperRegistrationRequest(developer_id="dev_user_2", email="user2@prism.io")
    )

    with pytest.raises(ValueError, match="already registered"):
        identity_service.update_profile(
            "dev_user_2", DeveloperUpdateRequest(email="user1@prism.io")
        )
