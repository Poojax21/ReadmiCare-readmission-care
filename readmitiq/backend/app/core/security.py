"""
ReadmitIQ — Security & HIPAA-Ready Auth
JWT authentication, RBAC, and audit logging.
"""

import logging
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Optional

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

logger = logging.getLogger(__name__)
security = HTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class Role(str, Enum):
    ADMIN = "admin"
    CLINICIAN = "clinician"
    ANALYST = "analyst"
    VIEWER = "viewer"


ROLE_PERMISSIONS: dict[Role, set[str]] = {
    Role.ADMIN:     {"read", "write", "retrain", "admin"},
    Role.CLINICIAN: {"read", "write"},
    Role.ANALYST:   {"read", "retrain"},
    Role.VIEWER:    {"read"},
}


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(
    subject: str,
    role: Role,
    expires_delta: Optional[timedelta] = None,
) -> str:
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(hours=settings.JWT_EXPIRY_HOURS)
    )
    payload = {
        "sub": subject,
        "role": role.value,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired token: {e}",
        )


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security),
) -> dict:
    return decode_token(credentials.credentials)


def require_permission(permission: str):
    """Dependency factory for route-level RBAC."""

    def _check(user: dict = Depends(get_current_user)) -> dict:
        role = Role(user.get("role", "viewer"))
        if permission not in ROLE_PERMISSIONS.get(role, set()):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{role.value}' lacks permission '{permission}'",
            )
        return user

    return _check


def audit_log(user_id: str, action: str, resource: str, detail: str = "") -> None:
    """HIPAA-compliant audit logging."""
    logger.info(
        "AUDIT",
        user_id=user_id,
        action=action,
        resource=resource,
        detail=detail,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
