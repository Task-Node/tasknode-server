"""Add runtime and removal columns

Revision ID: d98166c1dda2
Revises: abb745357a1c
Create Date: 2024-12-04 20:50:07.747972

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "d98166c1dda2"
down_revision = "abb745357a1c"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("jobs", sa.Column("upload_removed", sa.Boolean(), nullable=True))
    op.add_column("jobs", sa.Column("response_removed", sa.Boolean(), nullable=True))
    # fill in existing rows with False
    op.execute("UPDATE jobs SET upload_removed = FALSE, response_removed = FALSE")
    op.alter_column("jobs", "upload_removed", nullable=False)
    op.alter_column("jobs", "response_removed", nullable=False)
    op.add_column("jobs", sa.Column("runtime", sa.BigInteger(), nullable=True))


def downgrade() -> None:
    op.drop_column("jobs", "runtime")
    op.drop_column("jobs", "response_removed")
    op.drop_column("jobs", "upload_removed")
