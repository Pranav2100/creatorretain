"""create creator profile tables

Revision ID: 7d2c95b1e4af
Revises: c3f81a04d7be
Create Date: 2026-09-06 02:10:00.000000

"""
import uuid
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "7d2c95b1e4af"
down_revision: Union[str, Sequence[str], None] = "c3f81a04d7be"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


CATEGORIES = [
    ("food", "Food"),
    ("fashion", "Fashion"),
    ("beauty", "Beauty"),
    ("skincare", "Skincare"),
    ("fitness", "Fitness"),
    ("travel", "Travel"),
    ("tech", "Tech"),
    ("gaming", "Gaming"),
    ("education", "Education"),
    ("lifestyle", "Lifestyle"),
    ("finance", "Finance"),
    ("parenting", "Parenting"),
    ("comedy", "Comedy"),
    ("music", "Music"),
    ("art", "Art"),
]


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()

    availability = postgresql.ENUM(
        "AVAILABLE",
        "LIMITED",
        "UNAVAILABLE",
        name="creator_availability",
        create_type=False,
    )
    verification = postgresql.ENUM(
        "UNVERIFIED",
        "PENDING",
        "VERIFIED",
        name="creator_verification_status",
        create_type=False,
    )
    profile_status = postgresql.ENUM(
        "DRAFT",
        "PUBLISHED",
        "SUSPENDED",
        name="creator_profile_status",
        create_type=False,
    )
    platform = postgresql.ENUM(
        "INSTAGRAM",
        "YOUTUBE",
        "TIKTOK",
        name="social_platform",
        create_type=False,
    )
    deliverable = postgresql.ENUM(
        "REEL",
        "POST",
        "STORY",
        "VIDEO",
        "UGC",
        "EDITING",
        "STRATEGY",
        name="deliverable_type",
        create_type=False,
    )

    for enum_type in (
        availability,
        verification,
        profile_status,
        platform,
        deliverable,
    ):
        enum_type.create(bind, checkfirst=True)

    json_type = postgresql.JSONB(astext_type=sa.Text())

    op.create_table(
        "creator_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("headline", sa.String(length=120), nullable=True),
        sa.Column("bio", sa.Text(), nullable=True),
        sa.Column("city", sa.String(length=100), nullable=True),
        sa.Column("country", sa.String(length=2), nullable=True),
        sa.Column("languages", json_type, nullable=False),
        sa.Column("skills", json_type, nullable=False),
        sa.Column(
            "monthly_retainer_min",
            sa.Numeric(precision=12, scale=2),
            nullable=True,
        ),
        sa.Column(
            "currency",
            sa.String(length=3),
            server_default="INR",
            nullable=False,
        ),
        sa.Column("availability", availability, nullable=False),
        sa.Column(
            "verification_status", verification, nullable=False
        ),
        sa.Column(
            "verified_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column("status", profile_status, nullable=False),
        sa.Column(
            "is_hidden",
            sa.Boolean(),
            server_default=sa.false(),
            nullable=False,
        ),
        sa.Column(
            "completeness",
            sa.SmallInteger(),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "boosted_until",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "deleted_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("workspace_id"),
    )
    op.create_index(
        "ix_creator_profiles_city", "creator_profiles", ["city"]
    )
    op.create_index(
        "ix_creator_profiles_country", "creator_profiles", ["country"]
    )
    op.create_index(
        "ix_creator_profiles_status", "creator_profiles", ["status"]
    )
    op.create_index(
        "ix_creator_profiles_completeness",
        "creator_profiles",
        ["completeness"],
    )
    op.create_index(
        "ix_creator_profiles_boosted_until",
        "creator_profiles",
        ["boosted_until"],
    )
    op.create_index(
        "ix_creator_profiles_discovery",
        "creator_profiles",
        ["status", "is_hidden", "availability"],
    )

    op.create_table(
        "content_categories",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("slug", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.true(),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "deleted_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )

    op.create_table(
        "creator_categories",
        sa.Column(
            "profile_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "category_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["content_categories.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["profile_id"],
            ["creator_profiles.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("profile_id", "category_id"),
    )
    op.create_index(
        "ix_creator_categories_category_id",
        "creator_categories",
        ["category_id"],
    )

    op.create_table(
        "creator_social_accounts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "profile_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("platform", platform, nullable=False),
        sa.Column("handle", sa.String(length=100), nullable=False),
        sa.Column("profile_url", sa.Text(), nullable=True),
        sa.Column("claimed_followers", sa.Integer(), nullable=True),
        sa.Column(
            "claimed_engagement_rate",
            sa.Numeric(precision=5, scale=2),
            nullable=True,
        ),
        sa.Column("verified_followers", sa.Integer(), nullable=True),
        sa.Column(
            "verified_engagement_rate",
            sa.Numeric(precision=5, scale=2),
            nullable=True,
        ),
        sa.Column(
            "verified_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "last_synced_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "deleted_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["profile_id"],
            ["creator_profiles.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "profile_id",
            "platform",
            name="uq_social_account_profile_platform",
        ),
    )
    op.create_index(
        "ix_creator_social_accounts_profile_id",
        "creator_social_accounts",
        ["profile_id"],
    )
    op.create_index(
        "ix_social_platform_followers",
        "creator_social_accounts",
        ["platform", "claimed_followers"],
    )

    op.create_table(
        "creator_portfolio_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "profile_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("title", sa.String(length=150), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("platform", platform, nullable=True),
        sa.Column("external_url", sa.Text(), nullable=True),
        sa.Column("media_url", sa.Text(), nullable=True),
        sa.Column(
            "position",
            sa.SmallInteger(),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "deleted_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["profile_id"],
            ["creator_profiles.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_creator_portfolio_items_profile_id",
        "creator_portfolio_items",
        ["profile_id"],
    )

    op.create_table(
        "creator_rates",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "profile_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("deliverable_type", deliverable, nullable=False),
        sa.Column(
            "quantity",
            sa.SmallInteger(),
            server_default="1",
            nullable=False,
        ),
        sa.Column(
            "price",
            sa.Numeric(precision=12, scale=2),
            nullable=False,
        ),
        sa.Column(
            "currency",
            sa.String(length=3),
            server_default="INR",
            nullable=False,
        ),
        sa.Column("notes", sa.String(length=200), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "deleted_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["profile_id"],
            ["creator_profiles.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_creator_rates_profile_id",
        "creator_rates",
        ["profile_id"],
    )

    categories = sa.table(
        "content_categories",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("slug", sa.String),
        sa.column("name", sa.String),
    )

    op.bulk_insert(
        categories,
        [
            {"id": uuid.uuid4(), "slug": slug, "name": name}
            for slug, name in CATEGORIES
        ],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("creator_rates")
    op.drop_table("creator_portfolio_items")
    op.drop_table("creator_social_accounts")
    op.drop_table("creator_categories")
    op.drop_table("content_categories")
    op.drop_table("creator_profiles")

    bind = op.get_bind()

    for name in (
        "deliverable_type",
        "social_platform",
        "creator_profile_status",
        "creator_verification_status",
        "creator_availability",
    ):
        sa.Enum(name=name).drop(bind, checkfirst=True)
