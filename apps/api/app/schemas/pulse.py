from datetime import datetime

from pydantic import BaseModel


class PulseResponse(BaseModel):
    """
    What an open page polls to learn it is stale.

    Two numbers and nothing else. Anything richer would tempt a
    caller to render from it, and then every tab would be pulling
    whole objects every few seconds - and showing a page half
    built from one answer and half from another.
    """

    latest: datetime | None
    count: int
