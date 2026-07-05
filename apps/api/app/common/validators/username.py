import re


USERNAME_PATTERN = re.compile(r"^[a-z0-9._]+$")


def validate_username(username: str) -> None:
    username = username.strip()

    if username != username.lower():
        raise ValueError("Username must be lowercase.")

    if not 3 <= len(username) <= 30:
        raise ValueError(
            "Username must be between 3 and 30 characters."
        )

    if not USERNAME_PATTERN.fullmatch(username):
        raise ValueError(
            "Username may only contain lowercase letters, numbers, '.' and '_'."
        )

    if username.startswith((".", "_")):
        raise ValueError(
            "Username cannot start with '.' or '_'."
        )

    if username.endswith((".", "_")):
        raise ValueError(
            "Username cannot end with '.' or '_'."
        )

    if ".." in username:
        raise ValueError(
            "Username cannot contain consecutive periods."
        )

    if "__" in username:
        raise ValueError(
            "Username cannot contain consecutive underscores."
        )