from enum import Enum


class WorkspaceType(str, Enum):
    CREATOR = "creator"
    BRAND = "brand"
    AGENCY = "agency"