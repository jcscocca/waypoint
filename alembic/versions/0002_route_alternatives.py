"""route alternatives

Revision ID: 0002_route_alternatives
Revises: 0001_initial_schema
Create Date: 2026-06-23
"""
from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0002_route_alternatives"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "route_requests",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id_hash", sa.Text(), nullable=False),
        sa.Column("origin_label", sa.Text(), nullable=False),
        sa.Column("origin_latitude", sa.Float(), nullable=False),
        sa.Column("origin_longitude", sa.Float(), nullable=False),
        sa.Column("origin_display_latitude", sa.Float(), nullable=True),
        sa.Column("origin_display_longitude", sa.Float(), nullable=True),
        sa.Column("origin_location_type", sa.Text(), nullable=False),
        sa.Column("destination_label", sa.Text(), nullable=False),
        sa.Column("destination_latitude", sa.Float(), nullable=False),
        sa.Column("destination_longitude", sa.Float(), nullable=False),
        sa.Column("destination_display_latitude", sa.Float(), nullable=True),
        sa.Column("destination_display_longitude", sa.Float(), nullable=True),
        sa.Column("destination_location_type", sa.Text(), nullable=False),
        sa.Column("mode", sa.Text(), nullable=False),
        sa.Column("departure_date", sa.Date(), nullable=True),
        sa.Column("departure_time", sa.Text(), nullable=True),
        sa.Column("time_window", sa.Text(), nullable=True),
        sa.Column("preferences_json", sa.Text(), nullable=True),
        sa.Column("privacy_level", sa.Text(), nullable=False),
        sa.Column("provider", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("analysis_start_date", sa.Date(), nullable=True),
        sa.Column("analysis_end_date", sa.Date(), nullable=True),
        sa.Column("radii_m_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_route_requests_user_id_hash", "route_requests", ["user_id_hash"])

    op.create_table(
        "route_alternatives",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "route_request_id",
            sa.String(length=36),
            sa.ForeignKey("route_requests.id"),
            nullable=False,
        ),
        sa.Column("user_id_hash", sa.Text(), nullable=False),
        sa.Column("provider_route_id", sa.Text(), nullable=False),
        sa.Column("route_label", sa.Text(), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("duration_minutes", sa.Float(), nullable=True),
        sa.Column("distance_m", sa.Float(), nullable=True),
        sa.Column("transfer_count", sa.Integer(), nullable=False),
        sa.Column("walking_distance_m", sa.Float(), nullable=True),
        sa.Column("mode_mix", sa.Text(), nullable=False),
        sa.Column("summary_geometry", sa.Text(), nullable=True),
        sa.Column("provider", sa.Text(), nullable=False),
        sa.Column("provider_metadata_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_route_alternatives_route_request_id",
        "route_alternatives",
        ["route_request_id"],
    )
    op.create_index(
        "ix_route_alternatives_user_id_hash",
        "route_alternatives",
        ["user_id_hash"],
    )

    op.create_table(
        "route_segments",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "route_alternative_id",
            sa.String(length=36),
            sa.ForeignKey("route_alternatives.id"),
            nullable=False,
        ),
        sa.Column("user_id_hash", sa.Text(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("segment_type", sa.Text(), nullable=False),
        sa.Column("mode", sa.Text(), nullable=False),
        sa.Column("start_label", sa.Text(), nullable=False),
        sa.Column("start_latitude", sa.Float(), nullable=False),
        sa.Column("start_longitude", sa.Float(), nullable=False),
        sa.Column("end_label", sa.Text(), nullable=False),
        sa.Column("end_latitude", sa.Float(), nullable=False),
        sa.Column("end_longitude", sa.Float(), nullable=False),
        sa.Column("distance_m", sa.Float(), nullable=True),
        sa.Column("duration_minutes", sa.Float(), nullable=True),
        sa.Column("geometry", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_route_segments_route_alternative_id",
        "route_segments",
        ["route_alternative_id"],
    )
    op.create_index("ix_route_segments_user_id_hash", "route_segments", ["user_id_hash"])

    op.create_table(
        "route_context_summaries",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id_hash", sa.Text(), nullable=False),
        sa.Column(
            "route_alternative_id",
            sa.String(length=36),
            sa.ForeignKey("route_alternatives.id"),
            nullable=False,
        ),
        sa.Column(
            "route_segment_id",
            sa.String(length=36),
            sa.ForeignKey("route_segments.id"),
            nullable=True,
        ),
        sa.Column("context_label", sa.Text(), nullable=False),
        sa.Column("context_type", sa.Text(), nullable=False),
        sa.Column("radius_m", sa.Integer(), nullable=False),
        sa.Column("analysis_start_date", sa.Date(), nullable=False),
        sa.Column("analysis_end_date", sa.Date(), nullable=False),
        sa.Column("offense_category", sa.Text(), nullable=True),
        sa.Column("offense_subcategory", sa.Text(), nullable=True),
        sa.Column("nibrs_group", sa.Text(), nullable=True),
        sa.Column("incident_count", sa.Integer(), nullable=False),
        sa.Column("nearest_incident_m", sa.Float(), nullable=True),
        sa.Column("incidents_per_route", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_route_context_summaries_route_alternative_id",
        "route_context_summaries",
        ["route_alternative_id"],
    )
    op.create_index(
        "ix_route_context_summaries_route_segment_id",
        "route_context_summaries",
        ["route_segment_id"],
    )
    op.create_index(
        "ix_route_context_summaries_user_id_hash",
        "route_context_summaries",
        ["user_id_hash"],
    )


def downgrade() -> None:
    op.drop_table("route_context_summaries")
    op.drop_table("route_segments")
    op.drop_table("route_alternatives")
    op.drop_table("route_requests")
