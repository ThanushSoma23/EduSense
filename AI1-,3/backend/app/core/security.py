import jwt
import logging
from typing import Optional, Dict, Any
from fastapi import HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.config import settings
from app.db.supabase import db

logger = logging.getLogger(__name__)
security = HTTPBearer(auto_error=False)

def verify_token(credentials: Optional[HTTPAuthorizationCredentials] = Security(security)) -> Dict[str, Any]:
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    # Dev token check (ONLY permitted in APP_ENV=dev)
    if token.startswith("dev-token-"):
        if settings.APP_ENV != "dev":
            logger.warning(f"REJECTED dev token '{token}' in non-dev environment mode (APP_ENV='{settings.APP_ENV}')")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Dev tokens are disabled in non-development environment mode.",
            )

        if "admin" in token:
            user_id = "admin-1111-1111-1111-111111111111"
        elif "teacher" in token:
            user_id = "11111111-1111-1111-1111-111111111111"
        elif "student" in token:
            user_id = "22222222-2222-2222-2222-222222222222"
        else:
            raise HTTPException(status_code=401, detail="Invalid dev token.")

        profile = db.profiles.get(user_id)
        if not profile:
            raise HTTPException(status_code=401, detail="Profile not found for dev token.")
        return profile

    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            options={"verify_aud": False}
        )
        user_id = payload.get("sub") or payload.get("id")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token payload.")

        # Always load authoritative role and status from database profile!
        profile = db.profiles.get(user_id)
        if not profile:
            raise HTTPException(status_code=401, detail="User profile not found.")

        return profile
    except jwt.PyJWTError as e:
        logger.error(f"JWT Verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

# Aliases for backward compatibility
get_current_user = verify_token
require_active_user = verify_token

def require_teacher(current_user: Dict[str, Any] = Security(verify_token)) -> Dict[str, Any]:
    user_role = current_user.get("role")
    user_status = current_user.get("status", "active")

    if user_role != "teacher":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Teacher role required for this action."
        )

    if user_status == "pending":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Teacher account is pending admin approval."
        )

    if user_status == "rejected":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Teacher registration was rejected by administrator."
        )

    return current_user

def require_student(current_user: Dict[str, Any] = Security(verify_token)) -> Dict[str, Any]:
    user_role = current_user.get("role")
    if user_role not in ["student", "teacher", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Student access required."
        )
    return current_user

def require_admin(current_user: Dict[str, Any] = Security(verify_token)) -> Dict[str, Any]:
    user_role = current_user.get("role")
    if user_role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Administrator role required."
        )
    return current_user
