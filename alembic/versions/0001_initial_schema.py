"""initial schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-06-22
"""
from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "import_batches",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id_hash", sa.Text(), nullable=False),
        sa.Column("source_type", sa.Text(), nullable=False),
        sa.Column("original_filename", sa.Text(), nullable=False),
        sa.Column("file_hash_sha256", sa.Text(), nullable=False),
        sa.Column("parser_version", sa.Text(), nullable=False),
        sa.Column("detected_schema", sa.Text(), nullable=True),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("min_time_utc", sa.DateTime(timezone=True), nullable=True),
        sa.Column("max_time_utc", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("raw_retention_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("privacy_mode", sa.Text(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
    )
    op.create_index("ix_import_batches_user_id_hash", "import_batches", ["user_id_hash"])

    op.create_table(
        "place_clusters",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id_hash", sa.Text(), nullable=False),
        sa.Column("cluster_version", sa.Text(), nullable=False),
        sa.Column("cluster_method", sa.Text(), nullable=False),
        sa.Column("centroid_latitude", sa.Float(), nullable=False),
        sa.Column("centroid_longitude", sa.Float(), nullable=False),
        sa.Column("display_latitude", sa.Float(), nullable=True),
        sa.Column("display_longitude", sa.Float(), nullable=True),
        sa.Column("cluster_radius_m", sa.Float(), nullable=True),
        sa.Column("visit_count", sa.Integer(), nullable=False),
        sa.Column("total_dwell_minutes", sa.Float(), nullable=True),
        sa.Column("median_dwell_minutes", sa.Float(), nullable=True),
        sa.Column("first_seen_utc", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_seen_utc", sa.DateTime(timezone=True), nullable=True),
        sa.Column("dominant_days", sa.Text(), nullable=True),
        sa.Column("dominant_hours", sa.Text(), nullable=True),
        sa.Column("inferred_place_type", sa.Text(), nullable=False),
        sa.Column("sensitivity_class", sa.Text(), nullable=False),
        sa.Column("display_label", sa.Text(), nullable=True),
        sa.Column("label_source", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_place_clusters_user_id_hash", "place_clusters", ["user_id_hash"])

    op.create_table(
        "crime_incidents",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("external_incident_id", sa.Text(), nullable=True, unique=True),
        sa.Column("report_number", sa.Text(), nullable=True),
        sa.Column("offense_id", sa.Text(), nullable=True),
        sa.Column("offense_start_utc", sa.DateTime(timezone=True), nullable=True),
        sa.Column("offense_end_utc", sa.DateTime(timezone=True), nullable=True),
        sa.Column("report_utc", sa.DateTime(timezone=True), nullable=True),
        sa.Column("offense_category", sa.Text(), nullable=True),
        sa.Column("offense_subcategory", sa.Text(), nullable=True),
        sa.Column("nibrs_group", sa.Text(), nullable=True),
        sa.Column("precinct", sa.Text(), nullable=True),
        sa.Column("sector", sa.Text(), nullable=True),
        sa.Column("beat", sa.Text(), nullable=True),
        sa.Column("mcpp", sa.Text(), nullable=True),
        sa.Column("block_address", sa.Text(), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("source_dataset", sa.Text(), nullable=False),
        sa.Column("snapshot_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "staging_location_observations",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "import_id",
            sa.String(length=36),
            sa.ForeignKey("import_batches.id"),
            nullable=False,
        ),
        sa.Column("user_id_hash", sa.Text(), nullable=False),
        sa.Column("source_record_type", sa.Text(), nullable=False),
        sa.Column("source_record_hash", sa.Text(), nullable=True),
        sa.Column("observed_at_utc", sa.DateTime(timezone=True), nullable=True),
        sa.Column("start_time_utc", sa.DateTime(timezone=True), nullable=True),
        sa.Column("end_time_utc", sa.DateTime(timezone=True), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("accuracy_m", sa.Float(), nullable=True),
        sa.Column("activity_type", sa.Text(), nullable=True),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column("display_label", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("import_id", "source_record_hash", name="uq_staging_hash"),
    )
    op.create_index(
        "ix_staging_location_observations_import_id",
        "staging_location_observations",
        ["import_id"],
    )
    op.create_index(
        "ix_staging_location_observations_user_id_hash",
        "staging_location_observations",
        ["user_id_hash"],
    )

    op.create_table(
        "stop_visits",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "import_id",
            sa.String(length=36),
            sa.ForeignKey("import_batches.id"),
            nullable=False,
        ),
        sa.Column("user_id_hash", sa.Text(), nullable=False),
        sa.Column(
            "place_cluster_id",
            sa.String(length=36),
            sa.ForeignKey("place_clusters.id"),
            nullable=True,
        ),
        sa.Column("start_time_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_time_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_minutes", sa.Float(), nullable=False),
        sa.Column("local_date", sa.Date(), nullable=True),
        sa.Column("local_day_of_week", sa.Integer(), nullable=True),
        sa.Column("local_hour_start", sa.Integer(), nullable=True),
        sa.Column("centroid_latitude", sa.Float(), nullable=False),
        sa.Column("centroid_longitude", sa.Float(), nullable=False),
        sa.Column("radius_m", sa.Float(), nullable=True),
        sa.Column("accuracy_median_m", sa.Float(), nullable=True),
        sa.Column("source_basis", sa.Text(), nullable=False),
        sa.Column("point_count_used", sa.Integer(), nullable=True),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column("display_label", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_stop_visits_import_id", "stop_visits", ["import_id"])
    op.create_index("ix_stop_visits_user_id_hash", "stop_visits", ["user_id_hash"])
    op.create_index("ix_stop_visits_place_cluster_id", "stop_visits", ["place_cluster_id"])

    op.create_table(
        "place_crime_summaries",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id_hash", sa.Text(), nullable=False),
        sa.Column(
            "place_cluster_id",
            sa.String(length=36),
            sa.ForeignKey("place_clusters.id"),
            nullable=False,
        ),
        sa.Column("radius_m", sa.Integer(), nullable=False),
        sa.Column("analysis_start_date", sa.Date(), nullable=False),
        sa.Column("analysis_end_date", sa.Date(), nullable=False),
        sa.Column("offense_category", sa.Text(), nullable=True),
        sa.Column("offense_subcategory", sa.Text(), nullable=True),
        sa.Column("nibrs_group", sa.Text(), nullable=True),
        sa.Column("incident_count", sa.Integer(), nullable=False),
        sa.Column("nearest_incident_m", sa.Float(), nullable=True),
        sa.Column("incidents_per_visit", sa.Float(), nullable=True),
        sa.Column("incidents_per_hour_dwell", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_place_crime_summaries_user_id_hash",
        "place_crime_summaries",
        ["user_id_hash"],
    )
    op.create_index(
        "ix_place_crime_summaries_place_cluster_id",
        "place_crime_summaries",
        ["place_cluster_id"],
    )


def downgrade() -> None:
    op.drop_table("place_crime_summaries")
    op.drop_table("stop_visits")
    op.drop_table("staging_location_observations")
    op.drop_table("crime_incidents")
    op.drop_table("place_clusters")
    op.drop_table("import_batches")
