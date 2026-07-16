"""Unit tests for AuthService."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.models.enums import Role
from app.schemas.auth import LoginRequest, LogoutRequest, RegisterRequest
from app.schemas.token import RefreshTokenRequest
from app.services.auth_service import AuthService
from app.services.jwt_service import JWTService
from app.services.password_service import PasswordService
from shared.config import Settings
from shared.exceptions import DuplicateEmailError
from shared.exceptions.auth import (
    ExpiredTokenError,
    ForbiddenError,
    InactiveUserError,
    InvalidCredentialsError,
    InvalidTokenError,
    RevokedTokenError,
    UserNotFoundError,
)
from shared.exceptions.email import EmailDeliveryError


@pytest.fixture
def jwt_settings() -> Settings:
    return Settings(
        secret_key="x" * 32,
        jwt_algorithm="HS256",
        access_token_expire_minutes=30,
        refresh_token_expire_days=7,
    )


@pytest.fixture
def password_service() -> PasswordService:
    return PasswordService()


@pytest.fixture
def jwt_service(jwt_settings: Settings) -> JWTService:
    return JWTService(settings=jwt_settings)


@pytest.fixture
def user_repository() -> MagicMock:
    return MagicMock()


@pytest.fixture
def refresh_token_repository() -> MagicMock:
    return MagicMock()


@pytest.fixture
def email_verification_service() -> MagicMock:
    from app.services.email_verification_service import EmailVerificationService

    return MagicMock(spec=EmailVerificationService)


@pytest.fixture
def auth_service(
    user_repository: MagicMock,
    refresh_token_repository: MagicMock,
    password_service: PasswordService,
    jwt_service: JWTService,
    email_verification_service: MagicMock,
) -> AuthService:
    return AuthService(
        user_repository=user_repository,
        refresh_token_repository=refresh_token_repository,
        password_service=password_service,
        jwt_service=jwt_service,
        email_verification_service=email_verification_service,
    )


def _make_user(
    *,
    email: str = "user@example.com",
    password: str = "SecurePass1!",
    password_service: PasswordService,
    is_active: bool = True,
    is_verified: bool = True,
) -> MagicMock:
    user = MagicMock()
    user.id = uuid4()
    user.first_name = "Jane"
    user.last_name = "Doe"
    user.email = email
    user.password_hash = password_service.hash(password)
    user.role = Role.USER
    user.is_verified = is_verified
    user.is_active = is_active
    user.is_blocked = False
    user.created_at = datetime.now(tz=UTC)
    user.updated_at = datetime.now(tz=UTC)
    user.password_changed_at = datetime.now(tz=UTC)
    return user


def _make_refresh_token(
    *,
    token: str,
    user_id: object,
    expires_at: datetime,
    is_revoked: bool = False,
) -> MagicMock:
    stored = MagicMock()
    stored.id = uuid4()
    stored.user_id = user_id
    stored.token = token
    stored.expires_at = expires_at
    stored.is_revoked = is_revoked
    return stored


def test_register_creates_user(
    auth_service: AuthService,
    user_repository: MagicMock,
    password_service: PasswordService,
) -> None:
    user = _make_user(password_service=password_service)
    user_repository.create_user.return_value = user

    response = auth_service.register(
        RegisterRequest(
            first_name="Jane",
            last_name="Doe",
            email="user@example.com",
            password="SecurePass1!",
        ),
    )

    assert response.user.email == "user@example.com"
    user_repository.create_user.assert_called_once()
    assert "password_hash" in user_repository.create_user.call_args.kwargs
    assert user_repository.create_user.call_args.kwargs["password_hash"] != "SecurePass1!"


def test_register_sends_verification_email(
    auth_service: AuthService,
    user_repository: MagicMock,
    email_verification_service: MagicMock,
    password_service: PasswordService,
) -> None:
    user = _make_user(password_service=password_service)
    user_repository.create_user.return_value = user

    auth_service.register(
        RegisterRequest(
            first_name="Jane",
            last_name="Doe",
            email="user@example.com",
            password="SecurePass1!",
        ),
    )

    email_verification_service.send_verification_email.assert_called_once_with(user)


def test_register_succeeds_when_email_delivery_fails(
    auth_service: AuthService,
    user_repository: MagicMock,
    email_verification_service: MagicMock,
    password_service: PasswordService,
) -> None:
    user = _make_user(password_service=password_service)
    user_repository.create_user.return_value = user
    email_verification_service.send_verification_email.side_effect = (
        EmailDeliveryError("smtp down")
    )

    # Registration must not fail just because the verification email could not
    # be delivered; the user can request a resend.
    response = auth_service.register(
        RegisterRequest(
            first_name="Jane",
            last_name="Doe",
            email="user@example.com",
            password="SecurePass1!",
        ),
    )

    assert response.user.email == "user@example.com"


def test_register_duplicate_email_raises(
    auth_service: AuthService,
    user_repository: MagicMock,
) -> None:
    user_repository.create_user.side_effect = DuplicateEmailError("duplicate")

    with pytest.raises(DuplicateEmailError):
        auth_service.register(
            RegisterRequest(
                first_name="Jane",
                last_name="Doe",
                email="user@example.com",
                password="SecurePass1!",
            ),
        )


def test_login_success(
    auth_service: AuthService,
    user_repository: MagicMock,
    refresh_token_repository: MagicMock,
    password_service: PasswordService,
) -> None:
    user = _make_user(password_service=password_service)
    user_repository.get_user_by_email.return_value = user
    refresh_token_repository.create_refresh_token.return_value = MagicMock()

    response = auth_service.login(
        LoginRequest(email="user@example.com", password="SecurePass1!"),
    )

    assert response.access_token
    assert response.refresh_token
    assert response.user.email == "user@example.com"
    refresh_token_repository.create_refresh_token.assert_called_once()
    # The stored value must be a hash, never the raw refresh token.
    stored_hash = refresh_token_repository.create_refresh_token.call_args.kwargs[
        "token_hash"
    ]
    assert stored_hash != response.refresh_token
    assert len(stored_hash) == 64


def test_login_succeeds_when_email_unverified(
    auth_service: AuthService,
    user_repository: MagicMock,
    refresh_token_repository: MagicMock,
    password_service: PasswordService,
) -> None:
    """Login issues tokens for unverified users; gated routes enforce verification."""
    user = _make_user(password_service=password_service, is_verified=False)
    user_repository.get_user_by_email.return_value = user

    response = auth_service.login(
        LoginRequest(email="user@example.com", password="SecurePass1!"),
    )

    assert response.user.is_verified is False
    refresh_token_repository.create_refresh_token.assert_called_once()


def test_login_succeeds_after_verification(
    auth_service: AuthService,
    user_repository: MagicMock,
    refresh_token_repository: MagicMock,
    password_service: PasswordService,
) -> None:
    user = _make_user(password_service=password_service, is_verified=True)
    user_repository.get_user_by_email.return_value = user

    response = auth_service.login(
        LoginRequest(email="user@example.com", password="SecurePass1!"),
    )

    assert response.access_token
    assert response.refresh_token


def test_login_invalid_credentials(
    auth_service: AuthService,
    user_repository: MagicMock,
) -> None:
    user_repository.get_user_by_email.return_value = None

    with pytest.raises(InvalidCredentialsError):
        auth_service.login(
            LoginRequest(email="user@example.com", password="SecurePass1!"),
        )


def test_login_inactive_user(
    auth_service: AuthService,
    user_repository: MagicMock,
    password_service: PasswordService,
) -> None:
    user = _make_user(password_service=password_service, is_active=False)
    user_repository.get_user_by_email.return_value = user

    with pytest.raises(InactiveUserError, match="Your account has been disabled"):
        auth_service.login(
            LoginRequest(email="user@example.com", password="SecurePass1!"),
        )


def test_login_rejects_insufficient_role(
    auth_service: AuthService,
    user_repository: MagicMock,
    password_service: PasswordService,
) -> None:
    user = _make_user(password_service=password_service)
    user_repository.get_user_by_email.return_value = user

    with pytest.raises(ForbiddenError):
        auth_service.login(
            LoginRequest(email="user@example.com", password="SecurePass1!"),
            required_roles=frozenset({Role.ADMIN, Role.SUPER_ADMIN}),
        )


def test_refresh_rotates_token_atomically(
    auth_service: AuthService,
    user_repository: MagicMock,
    refresh_token_repository: MagicMock,
    password_service: PasswordService,
) -> None:
    user = _make_user(password_service=password_service)
    stored = _make_refresh_token(
        token="old-refresh-token",
        user_id=user.id,
        expires_at=datetime.now(tz=UTC) + timedelta(days=1),
    )
    refresh_token_repository.get_by_token_hash.return_value = stored
    user_repository.get_user_by_id.return_value = user

    response = auth_service.refresh(
        RefreshTokenRequest(refresh_token="old-refresh-token"),
    )

    assert response.access_token
    assert response.refresh_token != "old-refresh-token"
    # Rotation happens through a single atomic repository call, not a
    # separate create + revoke.
    refresh_token_repository.rotate_token.assert_called_once()
    rotate_kwargs = refresh_token_repository.rotate_token.call_args.kwargs
    assert rotate_kwargs["old_token_id"] == stored.id
    assert rotate_kwargs["new_token_hash"] != response.refresh_token
    refresh_token_repository.create_refresh_token.assert_not_called()


def test_refresh_lookup_uses_hash_not_raw_token(
    auth_service: AuthService,
    user_repository: MagicMock,
    refresh_token_repository: MagicMock,
    password_service: PasswordService,
) -> None:
    user = _make_user(password_service=password_service)
    stored = _make_refresh_token(
        token="raw-token",
        user_id=user.id,
        expires_at=datetime.now(tz=UTC) + timedelta(days=1),
    )
    refresh_token_repository.get_by_token_hash.return_value = stored
    user_repository.get_user_by_id.return_value = user

    auth_service.refresh(RefreshTokenRequest(refresh_token="raw-token"))

    lookup_arg = refresh_token_repository.get_by_token_hash.call_args.args[0]
    assert lookup_arg != "raw-token"
    assert len(lookup_arg) == 64


def test_refresh_reuse_detection_revokes_all_sessions(
    auth_service: AuthService,
    refresh_token_repository: MagicMock,
) -> None:
    user_id = uuid4()
    stored = _make_refresh_token(
        token="revoked-token",
        user_id=user_id,
        expires_at=datetime.now(tz=UTC) + timedelta(days=1),
        is_revoked=True,
    )
    refresh_token_repository.get_by_token_hash.return_value = stored

    with pytest.raises(RevokedTokenError):
        auth_service.refresh(RefreshTokenRequest(refresh_token="revoked-token"))

    # Reuse of a revoked token must nuke the entire session family.
    refresh_token_repository.revoke_all_tokens.assert_called_once_with(user_id)


def test_refresh_unknown_token_raises_invalid(
    auth_service: AuthService,
    refresh_token_repository: MagicMock,
) -> None:
    refresh_token_repository.get_by_token_hash.return_value = None

    with pytest.raises(InvalidTokenError):
        auth_service.refresh(RefreshTokenRequest(refresh_token="unknown"))


def test_refresh_expired_token_raises(
    auth_service: AuthService,
    refresh_token_repository: MagicMock,
) -> None:
    stored = _make_refresh_token(
        token="expired-token",
        user_id=uuid4(),
        expires_at=datetime.now(tz=UTC) - timedelta(days=1),
    )
    refresh_token_repository.get_by_token_hash.return_value = stored

    with pytest.raises(ExpiredTokenError):
        auth_service.refresh(RefreshTokenRequest(refresh_token="expired-token"))


def test_refresh_naive_expiry_is_treated_as_utc(
    auth_service: AuthService,
    user_repository: MagicMock,
    refresh_token_repository: MagicMock,
    password_service: PasswordService,
) -> None:
    user = _make_user(password_service=password_service)
    stored = _make_refresh_token(
        token="naive-token",
        user_id=user.id,
        expires_at=datetime.now() + timedelta(days=1),  # noqa: DTZ005 - naive on purpose
    )
    refresh_token_repository.get_by_token_hash.return_value = stored
    user_repository.get_user_by_id.return_value = user

    response = auth_service.refresh(RefreshTokenRequest(refresh_token="naive-token"))

    assert response.access_token


def test_refresh_user_not_found_raises(
    auth_service: AuthService,
    user_repository: MagicMock,
    refresh_token_repository: MagicMock,
) -> None:
    stored = _make_refresh_token(
        token="orphan-token",
        user_id=uuid4(),
        expires_at=datetime.now(tz=UTC) + timedelta(days=1),
    )
    refresh_token_repository.get_by_token_hash.return_value = stored
    user_repository.get_user_by_id.return_value = None

    with pytest.raises(UserNotFoundError):
        auth_service.refresh(RefreshTokenRequest(refresh_token="orphan-token"))


def test_refresh_inactive_user_raises(
    auth_service: AuthService,
    user_repository: MagicMock,
    refresh_token_repository: MagicMock,
    password_service: PasswordService,
) -> None:
    user = _make_user(password_service=password_service, is_active=False)
    stored = _make_refresh_token(
        token="inactive-token",
        user_id=user.id,
        expires_at=datetime.now(tz=UTC) + timedelta(days=1),
    )
    refresh_token_repository.get_by_token_hash.return_value = stored
    user_repository.get_user_by_id.return_value = user

    with pytest.raises(InactiveUserError, match="Your account has been disabled"):
        auth_service.refresh(RefreshTokenRequest(refresh_token="inactive-token"))


def test_refresh_rejects_insufficient_role(
    auth_service: AuthService,
    user_repository: MagicMock,
    refresh_token_repository: MagicMock,
    password_service: PasswordService,
) -> None:
    user = _make_user(password_service=password_service)
    stored = _make_refresh_token(
        token="user-token",
        user_id=user.id,
        expires_at=datetime.now(tz=UTC) + timedelta(days=1),
    )
    refresh_token_repository.get_by_token_hash.return_value = stored
    user_repository.get_user_by_id.return_value = user

    with pytest.raises(ForbiddenError):
        auth_service.refresh(
            RefreshTokenRequest(refresh_token="user-token"),
            required_roles=frozenset({Role.ADMIN, Role.SUPER_ADMIN}),
        )


def test_logout_revokes_token(
    auth_service: AuthService,
    refresh_token_repository: MagicMock,
) -> None:
    stored = _make_refresh_token(
        token="logout-token",
        user_id=uuid4(),
        expires_at=datetime.now(tz=UTC) + timedelta(days=1),
    )
    refresh_token_repository.get_by_token_hash.return_value = stored

    auth_service.logout(LogoutRequest(refresh_token="logout-token"))

    refresh_token_repository.revoke_token.assert_called_once_with(stored.id)


def test_logout_already_revoked_token_is_noop(
    auth_service: AuthService,
    refresh_token_repository: MagicMock,
) -> None:
    stored = _make_refresh_token(
        token="already-revoked",
        user_id=uuid4(),
        expires_at=datetime.now(tz=UTC) + timedelta(days=1),
        is_revoked=True,
    )
    refresh_token_repository.get_by_token_hash.return_value = stored

    auth_service.logout(LogoutRequest(refresh_token="already-revoked"))

    refresh_token_repository.revoke_token.assert_not_called()


def test_logout_invalid_token_raises(
    auth_service: AuthService,
    refresh_token_repository: MagicMock,
) -> None:
    refresh_token_repository.get_by_token_hash.return_value = None

    with pytest.raises(InvalidTokenError):
        auth_service.logout(LogoutRequest(refresh_token="missing"))


def test_stale_access_token_rejected_after_password_change(
    auth_service: AuthService,
    user_repository: MagicMock,
    jwt_service: JWTService,
    password_service: PasswordService,
) -> None:
    user = _make_user(password_service=password_service)
    issued_at = datetime.now(tz=UTC) - timedelta(hours=1)
    user.password_changed_at = datetime.now(tz=UTC)
    user_repository.get_user_by_id.return_value = user

    stale_token = jwt_service.create_access_token(
        user_id=user.id,
        email=user.email,
        role=user.role,
        password_changed_at=issued_at,
    )

    with pytest.raises(InvalidTokenError, match="password change"):
        auth_service.resolve_user_from_access_token(stale_token)
