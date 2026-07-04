from enum import Enum


class VerificationStatus(str, Enum):
    NOT_VERIFIED = "not_verified"
    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"