"""initial schema: all six tables + partial unique index against double bookings (ADR 001)

Revision ID: 0001
Revises:
Create Date: 2026-10-01 16:21:26.172513
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Copied (not imported) from models.py: migrations must not change when models do.
ACTIVE_BOOKING_PREDICATE = "status IN ('PENDING_PAYMENT', 'CONFIRMED')"


def upgrade() -> None:
    op.create_table(
        "courts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("indoor", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_courts")),
        sa.UniqueConstraint("name", name=op.f("uq_courts_name")),
    )
    op.create_table(
        "members",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("membership_tier", sa.String(length=20), nullable=False),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "membership_tier IN ('STANDARD', 'PREMIUM')", name=op.f("ck_members_membership_tier")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_members")),
        sa.UniqueConstraint("email", name=op.f("uq_members_email")),
    )
    op.create_table(
        "time_slots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("court_id", sa.Integer(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("end_time", sa.Time(), nullable=False),
        sa.CheckConstraint("end_time > start_time", name=op.f("ck_time_slots_end_after_start")),
        sa.ForeignKeyConstraint(
            ["court_id"], ["courts.id"], name=op.f("fk_time_slots_court_id_courts")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_time_slots")),
        sa.UniqueConstraint("court_id", "date", "start_time", name=op.f("uq_time_slots_court_id")),
    )
    op.create_table(
        "bookings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("time_slot_id", sa.Integer(), nullable=False),
        sa.Column("booked_by_member_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("total_price", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('PENDING_PAYMENT', 'CONFIRMED', 'CANCELLED', 'EXPIRED')",
            name=op.f("ck_bookings_status"),
        ),
        sa.ForeignKeyConstraint(
            ["booked_by_member_id"],
            ["members.id"],
            name=op.f("fk_bookings_booked_by_member_id_members"),
        ),
        sa.ForeignKeyConstraint(
            ["time_slot_id"], ["time_slots.id"], name=op.f("fk_bookings_time_slot_id_time_slots")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_bookings")),
    )
    op.create_index(
        "ix_bookings_booked_by_member_id_status", "bookings", ["booked_by_member_id", "status"]
    )
    # Partial unique index: at most one PENDING_PAYMENT/CONFIRMED booking per slot (ADR 001).
    # Supported by PostgreSQL and SQLite (>= 3.8), not by MySQL.
    op.create_index(
        "uq_bookings_active_time_slot",
        "bookings",
        ["time_slot_id"],
        unique=True,
        postgresql_where=sa.text(ACTIVE_BOOKING_PREDICATE),
        sqlite_where=sa.text(ACTIVE_BOOKING_PREDICATE),
    )

    op.create_table(
        "waitlist_entries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("time_slot_id", sa.Integer(), nullable=False),
        sa.Column("member_id", sa.Integer(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("notified_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["member_id"], ["members.id"], name=op.f("fk_waitlist_entries_member_id_members")
        ),
        sa.ForeignKeyConstraint(
            ["time_slot_id"],
            ["time_slots.id"],
            name=op.f("fk_waitlist_entries_time_slot_id_time_slots"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_waitlist_entries")),
        sa.UniqueConstraint(
            "time_slot_id", "position", name=op.f("uq_waitlist_entries_time_slot_id")
        ),
    )
    op.create_table(
        "participants",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("booking_id", sa.Integer(), nullable=False),
        sa.Column("member_id", sa.Integer(), nullable=False),
        sa.Column("share_amount", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("paid", sa.Boolean(), nullable=False),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["booking_id"], ["bookings.id"], name=op.f("fk_participants_booking_id_bookings")
        ),
        sa.ForeignKeyConstraint(
            ["member_id"], ["members.id"], name=op.f("fk_participants_member_id_members")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_participants")),
        sa.UniqueConstraint("booking_id", "member_id", name=op.f("uq_participants_booking_id")),
    )
    op.create_index(op.f("ix_participants_booking_id"), "participants", ["booking_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_participants_booking_id"), table_name="participants")
    op.drop_table("participants")
    op.drop_table("waitlist_entries")
    op.drop_index("uq_bookings_active_time_slot", table_name="bookings")
    op.drop_index("ix_bookings_booked_by_member_id_status", table_name="bookings")
    op.drop_table("bookings")
    op.drop_table("time_slots")
    op.drop_table("members")
    op.drop_table("courts")
