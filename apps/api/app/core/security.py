import re

from fastapi import HTTPException


def validate_password(password: str, confirm_password: str) -> None:
    """
    Validate password according to CreatorRetain password policy.
    """

    if password != confirm_password:
        raise HTTPException(
            status_code=400,
            detail="Passwords do not match.",
        )

    if len(password) < 8:
        raise HTTPException(
            status_code=400,
            detail="Password must be at least 8 characters long.",
        )

    if len(password) > 64:
        raise HTTPException(
            status_code=400,
            detail="Password cannot exceed 64 characters.",
        )

    if " " in password:
        raise HTTPException(
            status_code=400,
            detail="Password cannot contain spaces.",
        )

    if not re.search(r"[A-Z]", password):
        raise HTTPException(
            status_code=400,
            detail="Password must contain at least one uppercase letter.",
        )

    if not re.search(r"[a-z]", password):
        raise HTTPException(
            status_code=400,
            detail="Password must contain at least one lowercase letter.",
        )

    if not re.search(r"\d", password):
        raise HTTPException(
            status_code=400,
            detail="Password must contain at least one number.",
        )

    if not re.search(r"[!@#$%^&*(),.?\":{}|<>_\-+=/\\[\];'`~]", password):
        raise HTTPException(
            status_code=400,
            detail="Password must contain at least one special character.",
        )