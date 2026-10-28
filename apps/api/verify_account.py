"""
Your own account: the person, not the workspace.

Everything else in this API belongs to a workspace. This is the
one part that belongs to a human being, and until now there was
no way to change a name typed wrong at signup, or a password
someone else has learned.

Most of this suite is about what must NOT work: changing an email
without proving who you are, taking an address someone else signs
in with, and - the one that matters - whether a session opened
with the old password still works after the password changes.
"""

import os

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["JWT_SECRET_KEY"] = "test-secret"

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

import app.database.registry  # noqa: F401,E402
from app.database.models.base import Base  # noqa: E402

engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestSession = sessionmaker(
    bind=engine, autoflush=False, autocommit=False
)
Base.metadata.create_all(engine)

from fastapi.testclient import TestClient  # noqa: E402

from app.database.session import get_db  # noqa: E402
from app.main import app  # noqa: E402


def override_db():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_db
client = TestClient(app)

PASSED: list[str] = []
FAILED: list[str] = []

GOOD = "Str0ng!Passw0rd"


def ok(label):
    PASSED.append(label)
    print("PASS  " + label)


def bad(label, detail=""):
    FAILED.append(label)
    print("FAIL  " + label)

    if detail:
        print("        " + detail)


def check(label, response, expected, contains=None):
    good = response.status_code == expected

    if good and contains:
        good = contains.lower() in response.text.lower()

    if good:
        ok(label)
    else:
        bad(label, f"[{response.status_code}] {response.text[:220]}")

    return response


def register(email, first="Test", password=GOOD):
    return client.post(
        "/auth/register",
        json={
            "email": email,
            "password": password,
            "confirm_password": password,
            "first_name": first,
            "last_name": "User",
        },
    )


def sign_in(email, password=GOOD):
    r = client.post(
        "/auth/login", json={"email": email, "password": password}
    )

    if r.status_code != 200:
        return None

    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def main() -> int:
    print("--- a password has to be a password ---")

    for label, password in [
        ("too short", "Ab1"),
        ("no number at all", "abcdefghij"),
        ("no letter at all", "1234567890"),
        ("padded with a space", " Str0ngEnough "),
    ]:
        r = register(f"weak-{label.replace(' ', '')}@example.com",
                     password=password)

        if r.status_code == 422:
            ok(f"signing up is refused: {label}")
        else:
            bad(
                f"signing up is refused: {label}",
                f"[{r.status_code}] accepted {password!r}",
            )

    check(
        "and a real one is accepted",
        register("sam@example.com", "Sam"),
        201,
    )

    sam = sign_in("sam@example.com")
    assert sam, "could not sign in after registering"

    print("\n--- your own details ---")

    check(
        "you can read yourself",
        client.get("/auth/me", headers=sam),
        200,
        contains="sam@example.com",
    )

    check(
        "a stranger cannot",
        client.get("/auth/me"),
        401,
    )

    check(
        "a name typed wrong at signup can be fixed",
        client.patch(
            "/auth/me",
            json={"first_name": "Samira", "last_name": "Rao"},
            headers=sam,
        ),
        200,
        contains="Samira",
    )

    r = client.get("/auth/me", headers=sam).json()

    if r["last_name"] == "Rao" and r["email"] == "sam@example.com":
        ok("it changed what was sent and nothing else")
    else:
        bad("it changed only what was sent", str(r))

    check(
        "a name cannot be blanked",
        client.patch(
            "/auth/me", json={"first_name": ""}, headers=sam
        ),
        422,
    )

    print("\n--- a job title, which creators will read ---")

    check(
        "it starts empty for someone who signed up alone",
        client.get("/auth/me", headers=sam),
        200,
        contains='"job_title":null',
    )

    check(
        "and can be set",
        client.patch(
            "/auth/me",
            json={"job_title": "Talent Manager", "phone": "+919876543210"},
            headers=sam,
        ),
        200,
        contains="Talent Manager",
    )

    kept = client.get("/auth/me", headers=sam).json()

    if kept["phone"] == "+919876543210":
        ok("the phone is kept alongside it")
    else:
        bad("the phone is kept", str(kept))

    check(
        "and cleared again, for someone who leaves",
        client.patch(
            "/auth/me",
            json={"job_title": "  "},
            headers=sam,
        ),
        200,
        contains='"job_title":null',
    )

    client.patch(
        "/auth/me",
        json={"job_title": "Talent Manager"},
        headers=sam,
    )

    print("\n--- changing the address you sign in with ---")

    check(
        "not without the password",
        client.patch(
            "/auth/me",
            json={"email": "samira@example.com"},
            headers=sam,
        ),
        400,
        contains="password",
    )

    check(
        "nor with the wrong one",
        client.patch(
            "/auth/me",
            json={
                "email": "samira@example.com",
                "current_password": "NotTheP4ssword",
            },
            headers=sam,
        ),
        400,
    )

    register("taken@example.com", "Taken")

    check(
        "nor to one someone else signs in with",
        client.patch(
            "/auth/me",
            json={
                "email": "taken@example.com",
                "current_password": GOOD,
            },
            headers=sam,
        ),
        400,
        contains="already in use",
    )

    check(
        "but yes with the password",
        client.patch(
            "/auth/me",
            json={
                "email": "Samira@Example.com",
                "current_password": GOOD,
            },
            headers=sam,
        ),
        200,
    )

    moved = client.get("/auth/me", headers=sam).json()

    if moved["email"] == "samira@example.com":
        ok("and it is stored lowercase, as addresses are compared")
    else:
        bad("the new email is lowercased", moved["email"])

    if moved["email_verified"] is False:
        ok("the new address is not treated as proven")
    else:
        bad("a changed email is still marked verified")

    if sign_in("samira@example.com") and not sign_in("sam@example.com"):
        ok("the new address signs in and the old one does not")
    else:
        bad("signing in follows the new address")

    print("\n--- changing your password ---")

    before = sign_in("samira@example.com")
    assert before, "could not open a session to invalidate"

    check(
        "not without the current one",
        client.post(
            "/auth/change-password",
            json={
                "current_password": "WrongOne123",
                "new_password": "An0therGoodOne",
                "confirm_password": "An0therGoodOne",
            },
            headers=before,
        ),
        400,
    )

    check(
        "not when the two new ones differ",
        client.post(
            "/auth/change-password",
            json={
                "current_password": GOOD,
                "new_password": "An0therGoodOne",
                "confirm_password": "An0therGoodTwo",
            },
            headers=before,
        ),
        400,
        contains="do not match",
    )

    check(
        "not to a weak one",
        client.post(
            "/auth/change-password",
            json={
                "current_password": GOOD,
                "new_password": "short",
                "confirm_password": "short",
            },
            headers=before,
        ),
        422,
    )

    check(
        "not to the one you already have",
        client.post(
            "/auth/change-password",
            json={
                "current_password": GOOD,
                "new_password": GOOD,
                "confirm_password": GOOD,
            },
            headers=before,
        ),
        400,
        contains="already have",
    )

    # Two sessions, so the one that does the changing and the one
    # that merely existed can be told apart afterwards.
    elsewhere = sign_in("samira@example.com")

    changed = check(
        "and yes with everything right",
        client.post(
            "/auth/change-password",
            json={
                "current_password": GOOD,
                "new_password": "An0therGoodOne",
                "confirm_password": "An0therGoodOne",
            },
            headers=before,
        ),
        200,
    )

    if changed.status_code == 200:
        now = {
            "Authorization": (
                f"Bearer {changed.json()['access_token']}"
            )
        }

        check(
            "the browser that changed it is handed a working token",
            client.get("/auth/me", headers=now),
            200,
        )

        check(
            "the session open elsewhere is over",
            client.get("/auth/me", headers=elsewhere),
            401,
            contains="sign in again",
        )

        check(
            "so is the token that sent the change",
            client.get("/auth/me", headers=before),
            401,
        )

        if sign_in("samira@example.com", "An0therGoodOne"):
            ok("the new password signs in")
        else:
            bad("the new password signs in")

        if sign_in("samira@example.com", GOOD):
            bad("the old password still signs in")
        else:
            ok("and the old one does not")

        # Somebody else's sessions are nobody else's business.
        other = sign_in("taken@example.com")

        check(
            "another account's session is untouched",
            client.get("/auth/me", headers=other),
            200,
        )

    print(f"\n{len(PASSED)} passed, {len(FAILED)} failed")

    for label in FAILED:
        print("  FAILED:", label)

    return 1 if FAILED else 0


if __name__ == "__main__":
    raise SystemExit(main())
