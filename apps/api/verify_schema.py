"""
Does the schema the migrations build match the one the models
expect?

Every other suite in this directory builds its database with
create_all, straight from the models. That is fast and it keeps
them honest about behaviour, but it means not one of them has
ever executed a migration - so a migration that builds something
subtly different from the model is invisible to all of them.

That gap is not hypothetical. It produced a retainer_request enum
whose labels did not match what SQLAlchemy writes, and the first
thing that noticed was a 500 in somebody's face. verify_migrations
now catches that particular shape by reading the migration files
as text. This catches the rest, by looking at a real migrated
database and comparing it with the metadata column by column -
which is how a table that was missing deleted_at got found, a
column no amount of reading the enum labels would have revealed.

Needs a PostgreSQL DATABASE_URL and runs `alembic upgrade head`
against it first. Safe to point at a real database: everything
it writes happens inside a transaction that is rolled back, and
the comparison itself only reads.

    DATABASE_URL=postgresql+psycopg://... uv run python verify_schema.py
"""

import os
import sys
import uuid

# The same place alembic looks.
#
# env.py takes the URL from app settings, which read .env - so
# `alembic upgrade head` works with nothing exported, and a check
# that insisted on a shell variable would be the odd one out and
# would fail for somebody whose database is configured perfectly
# well. The environment still wins when it is set, which is how
# this gets pointed at a scratch database instead.
DATABASE_URL = os.environ.get("DATABASE_URL", "")

if not DATABASE_URL:
    try:
        from app.core.settings import settings

        DATABASE_URL = settings.DATABASE_URL
    except Exception as e:
        print(f"Could not read DATABASE_URL from settings: {e}")
        sys.exit(2)

if not DATABASE_URL:
    print(
        "No DATABASE_URL, in the environment or in .env. This "
        "needs the database the migrations are meant for."
    )
    sys.exit(2)

if DATABASE_URL.startswith("sqlite"):
    print(
        "This one needs PostgreSQL - the point is to execute the "
        "migrations, and they are written for Postgres.\n"
        "The other suites are the ones that run on SQLite."
    )
    sys.exit(2)

os.environ.setdefault("JWT_SECRET_KEY", "schema-check")

from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from sqlalchemy import create_engine, inspect  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

import app.database.registry  # noqa: F401,E402
from app.common.permissions import (  # noqa: E402
    WorkspacePermission as P,
)
from app.database.models.base import Base  # noqa: E402
from app.database.models.workspace_custom_role import (  # noqa: E402
    WorkspaceCustomRole,
)

PASSED: list[str] = []
FAILED: list[str] = []


def ok(label):
    PASSED.append(label)
    print("PASS  " + label)


def bad(label, detail=""):
    FAILED.append(label)
    print("FAIL  " + label)

    if detail:
        print("        " + detail)


print("=" * 62)
print("Running every migration")
print("=" * 62)

config = Config("alembic.ini")
config.set_main_option("sqlalchemy.url", DATABASE_URL)

try:
    command.upgrade(config, "head")
    ok("the whole chain applies")
except Exception as e:
    bad("the chain failed to apply", str(e)[:300])
    print(f"\n{len(PASSED)} passed, {len(FAILED)} failed")
    sys.exit(1)

engine = create_engine(DATABASE_URL)
inspector = inspect(engine)

print()
print("=" * 62)
print("Every table and column the models expect")
print("=" * 62)

live = set(inspector.get_table_names())
drift = 0

for name, table in sorted(Base.metadata.tables.items()):
    if name not in live:
        bad(f"{name} was never created")
        drift += 1
        continue

    have = {c["name"] for c in inspector.get_columns(name)}
    want = {c.name for c in table.columns}

    if want - have:
        bad(
            f"{name} is missing columns the model writes",
            f"missing: {sorted(want - have)}",
        )
        drift += 1

    if have - want:
        bad(
            f"{name} has columns no model knows about",
            f"extra: {sorted(have - want)}",
        )
        drift += 1

if drift == 0:
    ok(
        f"all {len(Base.metadata.tables)} tables match the models "
        f"column for column"
    )

print()
print("=" * 62)
print("A row through the real thing, then rolled back")
print("=" * 62)

Session = sessionmaker(bind=engine)
db = Session()

try:
    uid = uuid.uuid4()
    db.execute(
        Base.metadata.tables["users"].insert().values(
            id=uid,
            email=f"schema-probe-{uid}@example.com",
            password_hash="x",
            first_name="Schema",
            last_name="Probe",
        )
    )

    wsid = uuid.uuid4()
    db.execute(
        Base.metadata.tables["workspaces"].insert().values(
            id=wsid,
            display_name="Schema Probe",
            slug=f"schema_probe_{wsid.hex[:8]}",
            workspace_type="AGENCY",
            status="ACTIVE",
            verification_status="NOT_VERIFIED",
            owner_user_id=uid,
        )
    )

    db.add(
        WorkspaceCustomRole(
            workspace_id=wsid,
            name="Schema Probe Role",
            permissions=[
                P.VIEW_RETAINERS.value,
                P.MANAGE_RETAINERS.value,
            ],
            created_by_user_id=uid,
        )
    )
    db.flush()

    back = (
        db.query(WorkspaceCustomRole)
        .filter_by(name="Schema Probe Role")
        .one()
    )

    if back.granted == frozenset(
        {P.VIEW_RETAINERS, P.MANAGE_RETAINERS}
    ):
        ok("a permission set survives the round trip through JSONB")
    else:
        bad(
            "the permission set did not round-trip",
            str(back.permissions),
        )

    # The constraint has to be in the database, not only in the
    # model - a service check alone loses a race between two
    # requests naming the same role.
    nested = db.begin_nested()

    try:
        db.add(
            WorkspaceCustomRole(
                workspace_id=wsid,
                name="Schema Probe Role",
                permissions=[P.VIEW_RETAINERS.value],
            )
        )
        db.flush()
        nested.rollback()
        bad("the database accepted two roles with the same name")
    except Exception:
        nested.rollback()
        ok("the database itself refuses a duplicate role name")

finally:
    # Nothing written here is kept, so this is safe to point at a
    # database that matters.
    db.rollback()
    db.close()

print()
print(f"{len(PASSED)} passed, {len(FAILED)} failed")

if FAILED:
    sys.exit(1)
