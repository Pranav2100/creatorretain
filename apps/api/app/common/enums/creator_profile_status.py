from enum import Enum


class CreatorProfileStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    SUSPENDED = "suspended"
