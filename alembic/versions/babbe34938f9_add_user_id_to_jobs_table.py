"""Add user id to jobs table

Revision ID: babbe34938f9
Revises: e5acf335b645
Create Date: 2024-12-03 15:34:26.039028

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "babbe34938f9"
down_revision = "e5acf335b645"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("jobs", sa.Column("user_id", sa.BigInteger(), nullable=False))
    op.create_foreign_key(None, "jobs", "users", ["user_id"], ["id"])


def downgrade() -> None:
    op.drop_constraint(None, "jobs", type_="foreignkey")
    op.drop_column("jobs", "user_id")
