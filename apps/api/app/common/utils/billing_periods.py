"""
Working out which monthly periods a retainer should have.

Pure date arithmetic - no database, no models - because this is the
part that has to be exactly right and the part that is easiest to
get wrong. The service layer turns the dates this produces into
rows; cron will later call the same service on a timer.

The anchor-day rule
-------------------
A retainer starting on the 31st cannot renew on the 31st of
February. Rather than silently sliding dates around, the anchor is
clamped to 28 and the FIRST period simply runs short:

    start 31 Jan, anchor 28
      period 1   31 Jan -> 27 Feb   (28 days, short)
      period 2   28 Feb -> 27 Mar
      period 3   28 Mar -> 27 Apr

Every later period is a clean month. Clamping forward instead
(to 1 Mar) would make period 2 start before period 1 ended in some
months, which is worse than one short period.
"""

from dataclasses import dataclass
from datetime import date, timedelta

# The highest day-of-month that exists in every month. Anchoring
# above this is what creates the 31 February problem.
MAX_ANCHOR_DAY = 28

_ONE_DAY = timedelta(days=1)


@dataclass(frozen=True)
class Period:
    """One month of a retainer. Sequence is 1-based."""

    sequence: int
    start: date
    end: date

    @property
    def days(self) -> int:
        return (self.end - self.start).days + 1

    def contains(self, day: date) -> bool:
        return self.start <= day <= self.end


def anchor_day(start_date: date) -> int:
    """The day of the month that renewals land on."""
    return min(start_date.day, MAX_ANCHOR_DAY)


def add_months(start_date: date, months: int) -> date:
    """
    The anchor day, `months` months after the start month.

    Not the same as start_date + months: the day is the clamped
    anchor, so 31 Jan + 1 month is 28 Feb, not 2 March or 3 March.
    """
    if months == 0:
        return start_date

    index = (start_date.month - 1) + months

    return date(
        start_date.year + index // 12,
        index % 12 + 1,
        anchor_day(start_date),
    )


def period_start(start_date: date, sequence: int) -> date:
    """
    Where period `sequence` (1-based) begins.

    Period 1 begins on the start date itself, whatever day that is.
    Everything after it begins on the anchor day.
    """
    if sequence < 1:
        raise ValueError("Period sequence starts at 1.")

    return add_months(start_date, sequence - 1)


def periods_elapsed(start_date: date, as_of: date) -> int:
    """
    How many periods have begun on or before `as_of`.

    Zero when the retainer has not started yet - a retainer dated
    into the future has no periods, which is what lets a brand set
    one up in advance.
    """
    if as_of < start_date:
        return 0

    months = (as_of.year - start_date.year) * 12 + (
        as_of.month - start_date.month
    )

    # The month has arrived but the anchor day has not, so the
    # previous period is still running.
    if months > 0 and as_of.day < anchor_day(start_date):
        months -= 1

    return months + 1


def build_periods(
    start_date: date,
    as_of: date,
    end_date: date | None = None,
) -> list[Period]:
    """
    Every period that should exist as of `as_of`.

    Deterministic: the same arguments always produce the same list,
    which is what makes creating the missing ones safe to repeat.
    A period runs to the day before the next one starts, or to
    end_date when that falls first.
    """
    count = periods_elapsed(start_date, as_of)

    if count == 0:
        return []

    periods: list[Period] = []

    for sequence in range(1, count + 1):
        begins = period_start(start_date, sequence)

        if end_date is not None and begins > end_date:
            break

        next_begins = period_start(start_date, sequence + 1)
        ends = next_begins - _ONE_DAY

        if end_date is not None and ends > end_date:
            ends = end_date

        periods.append(
            Period(sequence=sequence, start=begins, end=ends),
        )

    return periods
