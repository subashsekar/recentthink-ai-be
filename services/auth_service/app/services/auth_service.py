"""Authentication use-case service."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from app.models.enums import Role
from app.models.user import User
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    LogoutRequest,
    RegisterRequest,
    RegisterResponse,
)
from app.schemas.responses import UserResponse
from app.schemas.token import RefreshTokenRequest, RefreshTokenResponse
from app.security.jwt import TokenType
from app.services.email_verification_service import EmailVerificationService
from app.services.jwt_service import JWTService
from app.services.password_service import PasswordService

from shared.exceptions import DuplicateEmailError
from shared.exceptions.auth import (
    EmailNotVerifiedError,
    ExpiredTokenError,
    ForbiddenError,
    InactiveUserError,
    InvalidCredentialsError,
    InvalidTokenError,
    RevokedTokenError,
    UserNotFoundError,
)
from shared.exceptions.email import EmailDeliveryError
from shared.logging import get_logger
from shared.logging.security import log_security_event

logger = get_logger(__name__)


class AuthService:
    """Orchestrates registration, login, token refresh, logout, and profile access."""

    def __init__(
        self,
        user_repository: UserRepository,
        refresh_token_repository: RefreshTokenRepository,
        password_service: PasswordService,
        jwt_service: JWTService,
        email_verification_service: EmailVerificationService,
    ) -> None:
        self._users = user_repository
        self._refresh_tokens = refresh_token_repository
        self._passwords = password_service
        self._jwt = jwt_service
        self._email_verification = email_verification_service

    def register(self, request: RegisterRequest) -> RegisterResponse:
        """Register a new user account and dispatch a verification email."""
        password_hash = self._passwords.hash(request.password)
        try:
            user = self._users.create_user(
                first_name=request.first_name,
                last_name=request.last_name,
                email=request.email,
                password_hash=password_hash,
            )
        except DuplicateEmailError:
            logger.warning("Registration failed: duplicate email %s", request.email)
            raise

        logger.info("User registered id=%s email=%s", user.id, user.email)
        log_security_event("registration", user_id=str(user.id), email=user.email)

        # Send the verification email automatically. A delivery failure must
        # not roll back a successful registration — the account exists and the
        # user can request a new email via the resend endpoint.
        try:
            self._email_verification.send_verification_email(user)
        except EmailDeliveryError:
            logger.warning(
                "Verification email delivery failed for user_id=%s; "
                "registration still succeeded",
                user.id,
            )

        return RegisterResponse(user=UserResponse.model_validate(user))

    def login(
        self,
        request: LoginRequest,
        *,
        required_roles: frozenset[Role] | None = None,
    ) -> LoginResponse:
        """Authenticate credentials and issue access and refresh tokens."""
        user = self._users.get_user_by_email(request.email)
        if user is None or not self._passwords.verify(
            request.password, user.password_hash
        ):
            logger.warning("Login failed for email=%s: invalid credentials", request.email)
            log_security_event("login_failure", email=str(request.email))
            raise InvalidCredentialsError("Invalid email or password.")

        if required_roles is not None and user.role not in required_roles:
            logger.warning(
                "Login failed for email=%s: insufficient role %s",
                request.email,
                user.role,
            )
            raise ForbiddenError("Admin privileges required.")

        if not user.is_active:
            logger.warning("Login failed for email=%s: inactive user", request.email)
            raise InactiveUserError("User account is inactive.")

        if not user.is_verified:
            logger.warning(
                "Login failed for email=%s: email not verified",
                request.email,
            )
            raise EmailNotVerifiedError(
                "Please verify your email address before logging in.",
            )

        access_token = self._jwt.create_access_token(
            user_id=user.id,
            email=user.email,
            role=user.role,
            password_changed_at=user.password_changed_at,
        )
        refresh_token = self._jwt.generate_refresh_token()
        expires_at = self._jwt.get_refresh_token_expiry()
        self._refresh_tokens.create_refresh_token(
            user_id=user.id,
            token_hash=self._jwt.hash_refresh_token(refresh_token),
            expires_at=expires_at,
        )

        logger.info("Login succeeded id=%s email=%s", user.id, user.email)
        log_security_event("login_success", user_id=str(user.id), email=user.email)
        return LoginResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            user=UserResponse.model_validate(user),
        )

    def refresh(
        self,
        request: RefreshTokenRequest,
        *,
        required_roles: frozenset[Role] | None = None,
    ) -> RefreshTokenResponse:
        """Validate a refresh token, rotate it, and return new credentials.

        Enforces refresh-token reuse detection: presenting an already-revoked
        token is treated as a compromised session and revokes every refresh
        token for that user.
        """
        token_hash = self._jwt.hash_refresh_token(request.refresh_token)
        stored = self._refresh_tokens.get_by_token_hash(token_hash)
        if stored is None:
            logger.warning("Refresh failed: token not found")
            raise InvalidTokenError("Invalid refresh token.")

        if stored.is_revoked:
            # Reuse of a revoked token indicates the token may have been
            # stolen. Revoke the entire token family for the user so neither
            # the attacker nor the legitimate client can continue the session.
            logger.warning(
                "SECURITY: refresh token reuse detected user_id=%s token_id=%s; "
                "revoking all sessions",
                stored.user_id,
                stored.id,
            )
            self._refresh_tokens.revoke_all_tokens(stored.user_id)
            raise RevokedTokenError("Refresh token has been revoked.")

        now = datetime.now(tz=UTC)
        expires_at = stored.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        if expires_at <= now:
            logger.warning("Refresh failed: token expired id=%s", stored.id)
            raise ExpiredTokenError("Refresh token has expired.")

        user = self._users.get_user_by_id(stored.user_id)
        if user is None:
            logger.warning("Refresh failed: user not found id=%s", stored.user_id)
            raise UserNotFoundError("User not found.")

        if not user.is_active:
            logger.warning("Refresh failed: inactive user id=%s", user.id)
            raise InactiveUserError("User account is inactive.")

        if required_roles is not None and user.role not in required_roles:
            logger.warning(
                "Refresh failed: insufficient role id=%s role=%s",
                user.id,
                user.role,
            )
            raise ForbiddenError("Admin privileges required.")

        new_refresh_token = self._jwt.generate_refresh_token()
        new_expires_at = self._jwt.get_refresh_token_expiry()

        # Atomic rotation: the old token is revoked and the new token is
        # created within a single transaction (see ``rotate_token``).
        self._refresh_tokens.rotate_token(
            old_token_id=stored.id,
            user_id=user.id,
            new_token_hash=self._jwt.hash_refresh_token(new_refresh_token),
            new_expires_at=new_expires_at,
        )

        access_token = self._jwt.create_access_token(
            user_id=user.id,
            email=user.email,
            role=user.role,
            password_changed_at=user.password_changed_at,
        )

        logger.info("Token refreshed for user id=%s", user.id)
        log_security_event("token_refresh", user_id=str(user.id))
        return RefreshTokenResponse(
            access_token=access_token,
            refresh_token=new_refresh_token,
        )

    def logout(self, request: LogoutRequest) -> None:
        """Revoke the provided refresh token."""
        token_hash = self._jwt.hash_refresh_token(request.refresh_token)
        stored = self._refresh_tokens.get_by_token_hash(token_hash)
        if stored is None:
            logger.warning("Logout failed: refresh token not found")
            raise InvalidTokenError("Invalid refresh token.")

        if not stored.is_revoked:
            self._refresh_tokens.revoke_token(stored.id)

        logger.info("Logout succeeded user_id=%s", stored.user_id)
        log_security_event("logout", user_id=str(stored.user_id))

    def resolve_user_from_access_token(self, access_token: str) -> User:
        """Decode an access token and load the corresponding user.

        Rejects tokens minted before the user's most recent password change so
        a reset/change invalidates existing access tokens.
        """
        payload = self._jwt.verify_token(access_token)
        if payload.get("token_type") != TokenType.ACCESS.value:
            raise InvalidTokenError("Invalid token type.")
        user_id_raw = payload.get("user_id")
        if not user_id_raw:
            raise InvalidTokenError("Token payload is missing user_id.")

        user = self._users.get_user_by_id(UUID(str(user_id_raw)))
        if user is None:
            raise UserNotFoundError("User not found.")

        self._reject_if_stale(payload, user)
        return user

    def _reject_if_stale(self, payload: dict[str, object], user: User) -> None:
        """Reject an access token issued before the user's last password change."""
        token_pwd_ts = payload.get("pwd_ts")
        current = self._password_timestamp(user.password_changed_at)
        if (
            current is not None
            and isinstance(token_pwd_ts, (int, float))
            and not isinstance(token_pwd_ts, bool)
            and token_pwd_ts < current
        ):
            logger.warning(
                "Access token rejected: invalidated by password change user_id=%s",
                user.id,
            )
            raise InvalidTokenError(
                "Session expired due to a password change. Please log in again.",
            )

    @staticmethod
    def _password_timestamp(value: datetime | None) -> float | None:
        """Return ``value`` as epoch seconds, or ``None`` when unset."""
        if value is None:
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value.timestamp()
