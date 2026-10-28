"""
Messaging: who may write to whom, and what stops them.

Anyone may write to anyone, which is a decision that only works
if the things protecting the person being written to actually
work. So most of this is about refusals.

A stranger's first message is a request. It sits in a separate
pile, it does not count towards an unread badge, and the sender
gets three messages and then silence until somebody answers.
Answering is accepting - there is no way to reply to a request
and leave it pending, because that state would mean nothing.
Either side can block, and a block stops both directions without
telling the blocked party anything.
"""

import os
import time

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["JWT_SECRET_KEY"] = "test-secret"

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

import app.database.registry  # noqa: F401,E402
from app.database.models.base import Base  # noqa: E402
from app.database.models.content_category import (  # noqa: E402
    ContentCategory,
)

engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestSession = sessionmaker(
    bind=engine, autoflush=False, autocommit=False
)
Base.metadata.create_all(engine)

import app.api.dependencies.services as services_module  # noqa: E402
from app.services.email.base import EmailSender  # noqa: E402


class _Silent(EmailSender):
    def send(self, message):
        pass


services_module.get_email_sender = lambda: _Silent()

from fastapi.testclient import TestClient  # noqa: E402

from app.database.session import get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.services.conversation import (  # noqa: E402
    NEW_CONVERSATIONS_A_DAY,
    UNANSWERED_LIMIT,
)


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

PASSWORD = "Str0ng!Passw0rd"


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
        bad(label, f"[{response.status_code}] {response.text[:200]}")

    return response


def register(email, first="Test"):
    client.post(
        "/auth/register",
        json={
            "email": email,
            "password": PASSWORD,
            "confirm_password": PASSWORD,
            "first_name": first,
            "last_name": "Person",
        },
    )

    login = client.post(
        "/auth/login",
        json={"email": email, "password": PASSWORD},
    )

    headers = {
        "Authorization": f"Bearer {login.json()['access_token']}"
    }

    client.patch(
        "/auth/me",
        json={"job_title": "Manager", "phone": "+919876543210"},
        headers=headers,
    )

    return headers


def workspace(headers, name, slug, kind):
    r = client.post(
        "/workspaces",
        json={
            "display_name": name,
            "username": slug,
            "workspace_type": kind,
        },
        headers=headers,
    )
    assert r.status_code == 201, r.text

    return r.json()["workspace"]["id"]


def say(headers, body, to=None, conversation=None):
    payload = {"body": body}

    if to:
        payload["to_workspace_id"] = to

    if conversation:
        payload["conversation_id"] = conversation

    return client.post(
        "/conversations/messages", json=payload, headers=headers
    )


def inbox(headers, requests=False):
    return client.get(
        "/conversations",
        params={"requests": str(requests).lower()},
        headers=headers,
    ).json()


def settle():
    """
    Waits out the clock.

    SQLite stamps to the nearest second, so a message sent in the
    same second as somebody's read mark reads as already read.
    PostgreSQL stamps to the microsecond and does not have this,
    but a check that only passes on the coarse clock by accident
    is not worth having.
    """
    time.sleep(1.1)


def seed_categories():
    db = TestSession()
    try:
        for slug, name in [("food", "Food")]:
            db.add(ContentCategory(slug=slug, name=name))
        db.commit()
    finally:
        db.close()


def main() -> int:
    seed_categories()

    brand = register("brand@example.com", "Bianca")
    brand_ws = workspace(brand, "TalentX", "talentx", "agency")

    nina = register("nina@example.com", "Nina")
    nina_ws = workspace(nina, "Nina Cooks", "ninacooks", "creator")

    raj = register("raj@example.com", "Raj")
    raj_ws = workspace(raj, "Raj Eats", "rajeats", "creator")

    print("--- a stranger writes ---")

    first = check(
        "anyone can open a thread with anyone",
        say(brand, "Hello, we like your work.", to=nina_ws),
        201,
    )

    thread_id = first.json()["id"]

    if first.json()["started_by_me"] is True:
        ok("the sender is not shown it as a request")
    else:
        bad("the sender sees their own thread as ordinary")

    hers = inbox(nina)

    if hers["total"] == 0:
        ok("it stays out of her inbox")
    else:
        bad("a stranger's message is kept out of the inbox", str(hers)[:200])

    if hers["unread_total"] == 0:
        ok("and off her unread count")
    else:
        bad("a request does not count as unread")

    if hers["requests_waiting"] == 1:
        ok("but the inbox says somebody is waiting")
    else:
        bad("the inbox counts what is waiting", str(hers)[:160])

    waiting = inbox(nina, requests=True)

    if waiting["total"] == 1:
        ok("and it is in her requests")
        assert waiting["conversations"][0]["preview"].startswith(
            "Hello"
        ), waiting
        ok("with a line of what was said")
    else:
        bad("the request is in the requests pile", str(waiting)[:200])

    r = client.get(
        f"/conversations/{thread_id}", headers=nina
    ).json()

    if r["is_request"] and not r["started_by_me"]:
        ok("she is told it is waiting on her")
    else:
        bad("the recipient sees it as a request", str(r)[:200])

    print("\n--- three strikes before an answer ---")

    say(brand, "Second.", conversation=thread_id)
    say(brand, "Third.", conversation=thread_id)

    check(
        f"a {UNANSWERED_LIMIT + 1}th message to somebody who has "
        "not answered is refused",
        say(brand, "Fourth.", conversation=thread_id),
        409,
        contains="not accepted",
    )

    print("\n--- she answers, which accepts ---")

    check(
        "she replies",
        say(nina, "Thanks, tell me more.", conversation=thread_id),
        201,
    )

    after = client.get(
        f"/conversations/{thread_id}", headers=nina
    ).json()

    if not after["is_request"]:
        ok("replying let them in")
    else:
        bad("a reply accepts the request")

    hers = inbox(nina)

    if hers["total"] == 1 and hers["requests_waiting"] == 0:
        ok("it moved from her requests into her inbox")
    else:
        bad("an accepted thread moves piles", str(hers)[:200])

    check(
        "and the sender is no longer rationed",
        say(brand, "Fourth, now allowed.", conversation=thread_id),
        201,
    )

    print("\n--- accepting without answering ---")

    second = say(brand, "Hello Raj.", to=raj_ws)
    raj_thread = second.json()["id"]

    check(
        "a request can be accepted outright",
        client.post(
            f"/conversations/{raj_thread}/accept", headers=raj
        ),
        200,
    )

    if inbox(raj)["total"] == 1:
        ok("which moves it without a word being said")
    else:
        bad("accepting moves it to the inbox")

    check(
        "accepting twice is refused plainly",
        client.post(
            f"/conversations/{raj_thread}/accept", headers=raj
        ),
        409,
        contains="not waiting on you",
    )

    check(
        "and the sender cannot accept their own",
        client.post(
            f"/conversations/{raj_thread}/accept", headers=brand
        ),
        409,
    )

    print("\n--- turning somebody away ---")

    third = say(nina, "Want to collaborate?", to=raj_ws)
    cold = third.json()["id"]

    check(
        "a request can be turned away",
        client.post(f"/conversations/{cold}/decline", headers=raj),
        204,
    )

    if inbox(raj, requests=True)["total"] == 0:
        ok("it leaves his requests")
    else:
        bad("a declined request leaves the pile")

    check(
        "and the sender cannot add to it",
        say(nina, "Hello?", conversation=cold),
        403,
        contains="could not be delivered",
    )

    r = say(raj, "Actually, go on.", conversation=cold)

    if r.status_code == 201:
        ok("but he can change his mind by answering")
    else:
        bad("declining can be reversed", r.text[:160])

    check(
        "which reopens it for them too",
        say(nina, "Great.", conversation=cold),
        201,
    )

    print("\n--- unread counts ---")

    before = inbox(nina)["unread_total"]

    settle()
    say(brand, "Something new.", conversation=thread_id)

    after_count = inbox(nina)["unread_total"]

    if after_count == before + 1:
        ok("a message from them counts as unread")
    else:
        bad(
            "an incoming message is unread",
            f"{before} then {after_count}",
        )

    say(nina, "Noted.", conversation=thread_id)

    if inbox(nina)["unread_total"] == 0:
        ok("and answering clears it, without a separate step")
    else:
        bad("replying marks a thread read")

    settle()
    say(brand, "One more.", conversation=thread_id)
    settle()
    client.post(f"/conversations/{thread_id}/read", headers=nina)

    if inbox(nina)["unread_total"] == 0:
        ok("so does opening it")
    else:
        bad("marking read clears the count")

    print("\n--- a message right after a read ---")

    # No settle() here on purpose. This is the case that was
    # broken: a read mark written by the application with
    # microseconds, against a message stamped by the database
    # clock, which truncates to the second on SQLite. Anything
    # arriving in the same second as the last read looked older
    # than it and was counted as already seen. Waiting a second
    # would hide exactly the bug this is here to catch.
    client.post(f"/conversations/{thread_id}/read", headers=nina)
    cleared = inbox(nina)["unread_total"]

    say(brand, "Sent moments later.", conversation=thread_id)

    if inbox(nina)["unread_total"] == cleared + 1:
        ok("counts as unread even when it lands in the same second")
    else:
        bad(
            "a message sent moments after a read is still unread",
            "it was counted as already seen",
        )

    say(brand, "And another.", conversation=thread_id)

    if inbox(nina)["unread_total"] == cleared + 2:
        ok("and so does the next one")
    else:
        bad("two messages in the same second both count")

    client.post(f"/conversations/{thread_id}/read", headers=nina)

    print("\n--- seen ---")

    mine = client.get(
        f"/conversations/{thread_id}", headers=brand
    ).json()

    if mine["seen_at"] is not None:
        ok("the sender can tell it has been read")
    else:
        bad("seen is reported back to the sender", str(mine)[:160])

    fresh = say(brand, "Unread by design.", to=raj_ws)

    if fresh.status_code == 201:
        unseen = client.get(
            f"/conversations/{raj_thread}", headers=brand
        ).json()

        # Raj accepted but has never opened it.
        if unseen["seen_at"] is None:
            ok("and that nothing has been read when it has not")
        else:
            bad("seen is null until somebody reads")

    print("\n--- blocking ---")

    check(
        "a workspace can block another",
        client.post(
            "/conversations/blocks",
            json={"workspace_id": nina_ws, "reason": "No thanks."},
            headers=raj,
        ),
        204,
    )

    check(
        "the blocked side is told nothing useful",
        say(nina, "Hello again.", conversation=cold),
        403,
        contains="could not be delivered",
    )

    check(
        "and the blocker cannot write either",
        say(raj, "Still here?", conversation=cold),
        403,
    )

    listed = client.get(
        "/conversations/blocks/list", headers=raj
    ).json()

    if listed["total"] == 1:
        ok("the block is listed for whoever made it")
    else:
        bad("blocks are listed", str(listed)[:160])

    check(
        "a block can be lifted",
        client.delete(
            f"/conversations/blocks/{nina_ws}", headers=raj
        ),
        204,
    )

    check(
        "and then they can talk again",
        say(nina, "Hello again.", conversation=cold),
        201,
    )

    check(
        "blocking yourself is refused",
        client.post(
            "/conversations/blocks",
            json={"workspace_id": raj_ws},
            headers=raj,
        ),
        409,
    )

    print("\n--- what one workspace cannot do ---")

    outsider = register("outsider@example.com", "Otto")
    workspace(outsider, "Outsider", "outsider", "brand")

    check(
        "somebody else's thread is not found",
        client.get(f"/conversations/{thread_id}", headers=outsider),
        404,
    )

    check(
        "nor can they write into it",
        say(outsider, "Butting in.", conversation=thread_id),
        404,
    )

    check(
        "nor mark it read",
        client.post(
            f"/conversations/{thread_id}/read", headers=outsider
        ),
        404,
    )

    check(
        "you cannot open a thread with yourself",
        say(brand, "Hello me.", to=brand_ws),
        409,
    )

    check(
        "a message of nothing but spaces is refused",
        say(brand, "   ", conversation=thread_id),
        409,
        contains="write something",
    )

    check(
        "and an empty one never reaches the service",
        say(brand, "", conversation=thread_id),
        422,
    )

    print("\n--- the ration on opening threads ---")

    # Counted by opening them until one is refused, rather than
    # by working out how many this workspace has already started.
    # The arithmetic version was wrong by one and passed anyway,
    # which is the kind of check that gives false comfort.
    opened = 0
    refusal = None
    stamp = 0

    while opened <= NEW_CONVERSATIONS_A_DAY + 1:
        stamp += 1
        target = register(f"t{stamp}@example.com", f"T{stamp}")
        target_ws = workspace(
            target, f"Target {stamp}", f"target{stamp}", "creator"
        )

        r = say(brand, "Hello.", to=target_ws)

        if r.status_code == 201:
            opened += 1
            continue

        refusal = r
        break

    if refusal is None:
        bad(
            "opening new threads is eventually refused",
            f"opened {opened} without being stopped",
        )
    elif refusal.status_code == 409 and "a day" in refusal.text:
        ok(
            f"opening new threads stops after "
            f"{NEW_CONVERSATIONS_A_DAY} in a day"
        )
    else:
        bad(
            "the refusal says why",
            f"[{refusal.status_code}] {refusal.text[:160]}",
        )

    check(
        "but talking in the ones you have is not affected",
        say(brand, "Still talking.", conversation=thread_id),
        201,
    )

    print(f"\n{len(PASSED)} passed, {len(FAILED)} failed")

    for label in FAILED:
        print("  FAILED:", label)

    return 1 if FAILED else 0


if __name__ == "__main__":
    raise SystemExit(main())
