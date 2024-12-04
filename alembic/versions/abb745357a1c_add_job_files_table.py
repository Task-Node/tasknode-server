""" Add job_files table

Revision ID: abb745357a1c
Revises: babbe34938f9
Create Date: 2024-12-03 22:40:10.186209

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "abb745357a1c"
down_revision = "babbe34938f9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "job_files",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("job_id", sa.UUID(), nullable=False),
        sa.Column("s3_bucket", sa.String(), nullable=False),
        sa.Column("s3_key", sa.String(), nullable=False),
        sa.Column("file_name", sa.String(), nullable=False),
        sa.Column("file_size", sa.BigInteger(), nullable=False),
        sa.Column("file_timestamp", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["job_id"],
            ["jobs.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("job_files")
