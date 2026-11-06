from fastapi import Depends
from sqlalchemy.orm import Session

from app.database.repositories.user import UserRepository
from app.database.repositories.workspace import WorkspaceRepository
from app.database.repositories.workspace_invitation import (
    WorkspaceInvitationRepository,
)
from app.database.repositories.creator_profile import (
    CreatorProfileRepository,
)
from app.database.repositories.brand import BrandRepository
from app.database.repositories.conversation import (
    ConversationRepository,
)
from app.database.repositories.discovery import DiscoveryRepository
from app.database.repositories.pulse import PulseRepository
from app.database.repositories.retainer import RetainerRepository
from app.database.repositories.billing import (
    BillingRepository,
)
from app.database.repositories.notification import (
    NotificationRepository,
)
from app.database.repositories.custom_role import (
    CustomRoleRepository,
)
from app.database.repositories.workspace_member import (
    WorkspaceMemberRepository,
)
from app.database.session import get_db
from app.services.email import get_email_sender
from app.services.workspace import WorkspaceService
from app.services.workspace_invitation import (
    WorkspaceInvitationService,
)
from app.services.brand import BrandService
from app.services.creator_profile import CreatorProfileService
from app.services.conversation import ConversationService
from app.services.discovery import DiscoveryService
from app.services.pulse import PulseService
from app.services.retainer import RetainerService
from app.services.workspace_plan import WorkspacePlanService
from app.services.billing import get_billing_provider
from app.services.billing.service import BillingService
from app.services.custom_role import CustomRoleService
from app.services.notification import NotificationService
from app.services.workspace_member import WorkspaceMemberService


def get_workspace_member_service(
    db: Session = Depends(get_db),
) -> WorkspaceMemberService:
    return WorkspaceMemberService(
        repository=WorkspaceMemberRepository(db),
        workspace_repository=WorkspaceRepository(db),
        custom_role_repository=CustomRoleRepository(db),
    )


def get_workspace_service(
    db: Session = Depends(get_db),
) -> WorkspaceService:
    return WorkspaceService(
        repository=WorkspaceRepository(db),
        member_service=get_workspace_member_service(db),
    )


def get_workspace_invitation_service(
    db: Session = Depends(get_db),
) -> WorkspaceInvitationService:
    return WorkspaceInvitationService(
        workspace_repository=WorkspaceRepository(db),
        member_repository=WorkspaceMemberRepository(db),
        invitation_repository=WorkspaceInvitationRepository(db),
        user_repository=UserRepository(db),
        member_service=get_workspace_member_service(db),
        email_sender=get_email_sender(),
    )


def get_creator_profile_service(
    db: Session = Depends(get_db),
) -> CreatorProfileService:
    return CreatorProfileService(
        repository=CreatorProfileRepository(db),
        member_service=get_workspace_member_service(db),
    )


def get_workspace_plan_service(
    db: Session = Depends(get_db),
) -> WorkspacePlanService:
    return WorkspacePlanService(
        workspace_repository=WorkspaceRepository(db),
        member_repository=WorkspaceMemberRepository(db),
        invitation_repository=WorkspaceInvitationRepository(db),
        member_service=get_workspace_member_service(db),
    )


def get_discovery_service(
    db: Session = Depends(get_db),
) -> DiscoveryService:
    return DiscoveryService(
        repository=DiscoveryRepository(db),
        member_service=get_workspace_member_service(db),
    )


def get_brand_service(
    db: Session = Depends(get_db),
) -> BrandService:
    return BrandService(
        repository=BrandRepository(db),
        workspace_repository=WorkspaceRepository(db),
    )


def get_retainer_service(
    db: Session = Depends(get_db),
) -> RetainerService:
    return RetainerService(
        repository=RetainerRepository(db),
        workspace_repository=WorkspaceRepository(db),
        member_service=get_workspace_member_service(db),
        notifications=get_notification_service(db),
    )


def get_conversation_service(
    db: Session = Depends(get_db),
) -> ConversationService:
    return ConversationService(
        repository=ConversationRepository(db),
        workspace_repository=WorkspaceRepository(db),
        member_service=get_workspace_member_service(db),
        notifications=get_notification_service(db),
        member_repository=WorkspaceMemberRepository(db),
    )


def get_pulse_service(
    db: Session = Depends(get_db),
) -> PulseService:
    return PulseService(
        repository=PulseRepository(db),
        member_service=get_workspace_member_service(db),
    )


def get_custom_role_service(
    db: Session = Depends(get_db),
) -> CustomRoleService:
    return CustomRoleService(
        repository=CustomRoleRepository(db),
        member_repository=WorkspaceMemberRepository(db),
    )


def get_notification_service(
    db: Session = Depends(get_db),
) -> NotificationService:
    return NotificationService(
        repository=NotificationRepository(db),
        member_repository=WorkspaceMemberRepository(db),
        retainer_repository=RetainerRepository(db),
        custom_role_repository=CustomRoleRepository(db),
        conversation_repository=ConversationRepository(db),
        email_sender=get_email_sender(),
    )


def get_billing_service(
    db: Session = Depends(get_db),
) -> BillingService:
    return BillingService(
        repository=BillingRepository(db),
        workspace_repository=WorkspaceRepository(db),
        provider=get_billing_provider(),
    )
