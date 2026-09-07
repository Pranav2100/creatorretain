from enum import Enum


class CreatorAvailability(str, Enum):
    AVAILABLE = "available"
    LIMITED = "limited"
    UNAVAILABLE = "unavailable"
