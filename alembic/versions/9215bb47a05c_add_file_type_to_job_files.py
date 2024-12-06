""" add file type to job_files

Revision ID: 9215bb47a05c
Revises: e3d02a8e5b1a
Create Date: 2024-12-05 20:03:21.947815

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "9215bb47a05c"
down_revision = "e3d02a8e5b1a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("DROP TYPE IF EXISTS filetype")
    op.execute("CREATE TYPE filetype AS ENUM ('OUTPUT_LOG', 'ERROR_LOG', 'GENERATED', 'ZIPPED_GENERATED')")
    op.add_column(
        "job_files",
        sa.Column(
            "file_type",
            sa.Enum(
                "OUTPUT_LOG",
                "ERROR_LOG",
                "GENERATED",
                "ZIPPED_GENERATED",
                name="filetype",
            ),
            nullable=True,
        ),
    )
    # default to GENERATED
    op.execute("UPDATE job_files SET file_type = 'GENERATED' WHERE file_type IS NULL")
    op.alter_column("job_files", "file_type", nullable=False)


def downgrade() -> None:
    op.drop_column("job_files", "file_type")
    op.execute("DROP TYPE IF EXISTS filetype")
