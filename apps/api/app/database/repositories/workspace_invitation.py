from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session, joinedload

from app.common.enums import WorkspaceInvitationStatus
from app.database.models.workspace_invitation import WorkspaceInvitation
from app.database.repositories.base import BaseRepository


class WorkspaceInvitationRepository(
    BaseRepository[WorkspaceInvitation]
):
    def __init__(self, db: Session):
        super().__init__(db, WorkspaceInvitation)

    def get_pending_by_workspace_and_email(
        self,
        workspace_id,
        email: str,
    ) -> WorkspaceInvitation | None:
        """
        Only a live invitation blocks a new one. A pending row that
        has lapsed is treated as absent, so an ignored invitation
        never locks an address out.
        """
        return (
            self.db.query(WorkspaceInvitation)
            .filter(
                WorkspaceInvitation.workspace_id == workspace_id,
                WorkspaceInvitation.email == email,
                WorkspaceInvitation.status
                == WorkspaceInvitationStatus.PENDING,
                WorkspaceInvitation.expires_at > datetime.now(UTC),
            )
            .first()
        )

    def get_by_token(
        self,
        token: str,
    ) -> WorkspaceInvitation | None:
        """
        Loads workspace and inviter too, so an invitation link can
        be previewed before the recipient has an account.
        """
        return (
            self.db.query(WorkspaceInvitation)
            .options(
                joinedload(WorkspaceInvitation.workspace),
                joinedload(WorkspaceInvitation.inviter),
            )
            .filter(
                WorkspaceInvitation.token == token,
            )
            .first()
        )
    
    def get_pending_by_user(
        self,
        user_id,
    ):
        return (
            self.db.query(self.model)
            .filter(
                self.model.user_id == user_id,
                self.model.status == WorkspaceInvitationStatus.PENDING,
            )
            .all()
        )
    
    def get_by_id(
        self,
        invitation_id: UUID,
    ) -> WorkspaceInvitation | None:
        return (
            self.db.query(self.model)
            .filter(
                self.model.id == invitation_id,
            )
            .first()
        )
    
    def save(
        self,
        invitation,
    ):
        self.db.add(invitation)
        self.db.commit()
        self.db.refresh(invitation)
        return invitation
    
    def get_by_email(
        self,
        email: str,
    ):
        """
        Every invitation ever sent to this address, newest first.

        History is kept visible so someone returning after months
        can still see who tried to reach them.
        """
        return (
            self.db.query(self.model)
            .options(
                joinedload(self.model.workspace),
                joinedload(self.model.inviter),
            )
            .filter(
                self.model.email == email.lower().strip(),
            )
            .order_by(
                self.model.created_at.desc(),
            )
            .all()
        )

    def get_live_pending_by_email(
        self,
        email: str,
    ):
        """Pending and not yet lapsed."""
        return (
            self.db.query(self.model)
            .filter(
                self.model.email == email.lower().strip(),
                self.model.status == WorkspaceInvitationStatus.PENDING,
                self.model.expires_at > datetime.now(UTC),
            )
            .all()
        )
    
    def get_by_workspace(
        self,
        workspace_id: UUID,
    ):
        return (
            self.db.query(self.model)
            .options(joinedload(self.model.inviter))
            .filter(
                self.model.workspace_id == workspace_id,
            )
            .order_by(
                self.model.created_at.desc(),
            )
            .all()
        )
    
    def get_pending_for_user(
        self,
        user_id: UUID,
    ):
        return (
            self.db.query(self.model)
            .filter(
                self.model.user_id == user_id,
                self.model.status == WorkspaceInvitationStatus.PENDING,
            )
            .all()
        )