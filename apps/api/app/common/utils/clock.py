from datetime import UTC, datetime

__all__ = ["as_utc", "is_past"]


def as_utc(value: datetime) -> datetime:
    """
    A datetime from this database, labelled UTC if it arrived bare.

    Every timestamp column here is declared timezone-aware and
    PostgreSQL returns it that way, but SQLite drops the offset on
    read. Comparing one of each does not quietly misbehave - it
    raises TypeError - so anything that compares a stored timestamp
    in Python has to normalise first. Values are stored as UTC
    either way; this only says so out loud.
    """
    return value if value.tzinfo else value.replace(tzinfo=UTC)


def is_past(value: datetime) -> bool:
    """
    Whether a stored timestamp has gone by.

    Both sides are normalised, including `now`, because a test may
    replace the clock with one that returns a naive time.
    """
    return as_utc(value) < as_utc(datetime.now(UTC))
