from enum import Enum


class DeliverableType(str, Enum):
    REEL = "reel"
    POST = "post"
    STORY = "story"
    VIDEO = "video"
    UGC = "ugc"
    EDITING = "editing"
    STRATEGY = "strategy"


# Display order, written out rather than inferred.
#
# Sorting by the enum column in SQL would be backend-dependent:
# Postgres orders by the order the type was declared, SQLite and
# others alphabetically. A month's work would then be grouped
# differently depending on the database, which is not something a
# list of deliverables should be sensitive to.
DELIVERABLE_TYPE_ORDER: tuple[DeliverableType, ...] = (
    DeliverableType.REEL,
    DeliverableType.VIDEO,
    DeliverableType.POST,
    DeliverableType.STORY,
    DeliverableType.UGC,
    DeliverableType.EDITING,
    DeliverableType.STRATEGY,
)

_RANK = {
    deliverable_type: index
    for index, deliverable_type in enumerate(DELIVERABLE_TYPE_ORDER)
}


def type_rank(deliverable_type: DeliverableType) -> int:
    """Where this type sits in display order."""
    return _RANK.get(deliverable_type, len(_RANK))
