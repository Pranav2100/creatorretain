from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class EmailMessage:
    to: str
    subject: str
    html_body: str
    text_body: str


class EmailSender(ABC):
    """
    Anything that can deliver an email.

    Keeping this abstract means the invitation flow never knows or
    cares which provider is behind it, so swapping one in later is
    a configuration change rather than a code change.
    """

    @abstractmethod
    def send(self, message: EmailMessage) -> None:
        ...
