from enum import Enum


class WorkspaceRole(str, Enum):
    """
    What someone is allowed to be in a workspace.

    Four ranks, and the order matters: an agency has a person who
    owns the business, people who run it, people who run accounts,
    and people who only need to see what was agreed. Collapsing
    the middle two - which this did until now - forced anyone who
    needed to review a creator's work to also be handed the
    ability to hire, remove and rewrite the company's page.
    """

    OWNER = "owner"
    ADMIN = "admin"
    MANAGER = "manager"
    MEMBER = "member"

    @property
    def rank(self) -> int:
        """
        How senior this is, as a number.

        Every question about who may act on whom is a comparison
        of two of these, so it is written once here rather than as
        a thicket of branches naming particular pairs - which is
        what made adding a fourth role a rewrite rather than a
        line.
        """
        return _RANK[self]

    def outranks(self, other: "WorkspaceRole") -> bool:
        return self.rank > other.rank


_RANK = {
    WorkspaceRole.MEMBER: 0,
    WorkspaceRole.MANAGER: 1,
    WorkspaceRole.ADMIN: 2,
    WorkspaceRole.OWNER: 3,
}
