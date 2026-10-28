import re

# Length does far more work than character classes do, which is
# why there is a floor here and no rule about punctuation. The
# ceiling is not about security - Argon2 will happily hash a
# novel - but about a form field nobody should be able to post a
# megabyte into.
MINIMUM_PASSWORD = 8
MAXIMUM_PASSWORD = 128

HAS_LETTER = re.compile(r"[A-Za-z]")
HAS_NUMBER = re.compile(r"[0-9]")


def validate_password(password: str) -> None:
    """
    Raises with a reason someone can act on.

    "Password is invalid" makes people guess, and guessing
    produces worse passwords rather than better ones, so each
    rule says what to do about it.
    """
    if len(password) < MINIMUM_PASSWORD:
        raise ValueError(
            f"Use at least {MINIMUM_PASSWORD} characters."
        )

    if len(password) > MAXIMUM_PASSWORD:
        raise ValueError(
            f"Keep it under {MAXIMUM_PASSWORD} characters."
        )

    if password.strip() != password:
        raise ValueError(
            "Remove the space at the start or end."
        )

    if not HAS_LETTER.search(password):
        raise ValueError("Include at least one letter.")

    if not HAS_NUMBER.search(password):
        raise ValueError("Include at least one number.")
