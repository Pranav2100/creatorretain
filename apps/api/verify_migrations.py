"""
Checks the migrations against the models without a database.

The other suites build their schema with create_all, straight from
the models, which means the migration files are never executed by
anything except a real PostgreSQL server. One whole class of bug
lives in that gap, and it bit: SQLAlchemy stores a Python enum by
its NAME, every enum type in this database therefore carries
uppercase labels, and a migration that wrote the lowercase values
instead made PostgreSQL reject every write to that column while
SQLite carried on perfectly happily.

So this reads the migration files as text, pulls out every enum
type it finds, and compares the labels against the Python enum
that the models actually bind to that type. No database, no
fixtures, runs in a second.
"""

import os
import re
import sys
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret")

sys.path.insert(0, str(Path(__file__).parent))

import sqlalchemy as sa  # noqa: E402

import app.database.registry  # noqa: F401,E402
from app.database.models.base import Base  # noqa: E402

VERSIONS = (
    Path(__file__).parent
    / "app"
    / "database"
    / "migrations"
    / "versions"
)

PASSED: list[str] = []
FAILED: list[str] = []


def ok(label: str) -> None:
    PASSED.append(label)
    print("PASS  " + label)


def bad(label: str, detail: str) -> None:
    FAILED.append(label)
    print("FAIL  " + label)
    print("        " + detail)


def enums_in_models() -> dict[str, list[str]]:
    """
    Every named enum type the models use, with the labels
    SQLAlchemy will actually write.
    """
    found: dict[str, list[str]] = {}

    for table in Base.metadata.tables.values():
        for column in table.columns:
            kind = column.type

            if not isinstance(kind, sa.Enum) or not kind.name:
                continue

            found[kind.name] = list(kind.enums)

    return found


# postgresql.ENUM("A", "B", name="x") or sa.Enum("A", name="x")
DECLARATION = re.compile(
    r"(?:postgresql\.ENUM|sa\.Enum)\s*\((?P<body>.*?)\)",
    re.DOTALL,
)
LABEL = re.compile(r"[\"']([A-Za-z0-9_]+)[\"']")
NAMED = re.compile(r"name\s*=\s*[\"'](?P<name>[a-z_]+)[\"']")

# A type is not always created in one go. Extending one in place
# is raw SQL - PostgreSQL has no other way - and reading only the
# Python declarations would report a type as it was first written
# rather than as it stands now.
ADDED_VALUE = re.compile(
    r"ALTER\s+TYPE\s+(?P<name>[a-z_]+)\s+ADD\s+VALUE"
    r"(?:\s+IF\s+NOT\s+EXISTS)?\s+'(?P<label>[A-Za-z0-9_]+)'",
    re.IGNORECASE,
)

# CREATE TYPE x AS ENUM ('A', 'B') - the same thing said in SQL
# rather than through SQLAlchemy.
CREATED_TYPE = re.compile(
    r"CREATE\s+TYPE\s+(?P<name>[a-z_]+)\s+AS\s+ENUM\s*\((?P<body>[^)]*)\)",
    re.IGNORECASE | re.DOTALL,
)


REVISION = re.compile(r"^revision:\s*str\s*=\s*[\"'](.+?)[\"']", re.M)
DOWN = re.compile(
    r"^down_revision[^=]*=\s*(?:[\"'](.+?)[\"']|None)", re.M
)


def in_order() -> list[Path]:
    """
    The migration files in the order Alembic will apply them.

    Filenames sort alphabetically, which is not the same thing at
    all, and a later migration correcting an earlier one only
    reads as a correction if you walk the chain.
    """
    by_revision: dict[str, Path] = {}
    parent: dict[str, str | None] = {}

    for path in VERSIONS.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        revision = REVISION.search(text)

        if not revision:
            continue

        down = DOWN.search(text)
        by_revision[revision.group(1)] = path
        parent[revision.group(1)] = down.group(1) if down else None

    children = {down: rev for rev, down in parent.items()}

    ordered: list[Path] = []
    current = children.get(None)

    while current:
        ordered.append(by_revision[current])
        current = children.get(current)

    return ordered


def enums_in_migrations() -> dict[str, tuple[str, ...]]:
    """
    Every enum type the migrations create, with the labels it ends
    up carrying once they have all run.
    """
    found: dict[str, tuple[str, ...]] = {}

    for path in in_order():
        text = path.read_text(encoding="utf-8")

        # Only what going forwards does. A downgrade legitimately
        # puts the old labels back, and reading those would have
        # this report the state of a database nobody is running.
        text = text.split("def downgrade", 1)[0]

        for match in DECLARATION.finditer(text):
            body = match.group("body")
            named = NAMED.search(body)

            if not named:
                continue

            # Everything quoted except the name= argument itself.
            labels = tuple(
                label
                for label in LABEL.findall(
                    body[: named.start()] + body[named.end() :]
                )
            )

            if not labels:
                # A reference rather than a declaration, e.g. a
                # column reusing a type made elsewhere.
                continue

            # Last one wins, because that is what the database
            # will be left holding.
            found[named.group("name")] = labels

        for match in CREATED_TYPE.finditer(text):
            labels = tuple(LABEL.findall(match.group("body")))

            if labels:
                found[match.group("name")] = labels

        # Applied after the declarations in this same file, since
        # a migration that creates a type and then extends it
        # means the sum of the two.
        for match in ADDED_VALUE.finditer(text):
            name = match.group("name")
            label = match.group("label")
            existing = found.get(name, ())

            if label not in existing:
                found[name] = existing + (label,)

    return found


def main() -> int:
    models = enums_in_models()
    migrations = enums_in_migrations()

    print(f"--- {len(models)} enum types in the models ---\n")

    for name, expected in sorted(models.items()):
        declared = migrations.get(name)

        if not declared:
            bad(
                f"{name} is declared somewhere in the migrations",
                "the models use this type but no migration creates it",
            )
            continue

        if set(declared) != set(expected):
            bad(
                f"{name} labels match the model",
                f"migrations leave {sorted(declared)}, SQLAlchemy "
                f"will write {sorted(expected)}",
            )
        else:
            ok(f"{name} labels match the model")

    print("\n--- types declared but unused ---")

    stray = sorted(set(migrations) - set(models))

    if stray:
        for name in stray:
            print(f"      {name} is created but no model binds to it")
    else:
        ok("every type a migration creates is used by a model")

    print(f"\n{len(PASSED)} passed, {len(FAILED)} failed")

    for label in FAILED:
        print("  FAILED:", label)

    return 1 if FAILED else 0


if __name__ == "__main__":
    raise SystemExit(main())
