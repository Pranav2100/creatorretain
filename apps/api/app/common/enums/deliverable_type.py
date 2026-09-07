from enum import Enum


class DeliverableType(str, Enum):
    REEL = "reel"
    POST = "post"
    STORY = "story"
    VIDEO = "video"
    UGC = "ugc"
    EDITING = "editing"
    STRATEGY = "strategy"
