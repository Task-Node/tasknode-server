"""update fargate_task_arn column to fargate_task_id

Revision ID: e3d02a8e5b1a
Revises: d98166c1dda2
Create Date: 2024-12-04 22:09:32.509816

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "e3d02a8e5b1a"
down_revision = "d98166c1dda2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("jobs", "fargate_task_arn", new_column_name="fargate_task_id")


def downgrade() -> None:
    op.alter_column("jobs", "fargate_task_id", new_column_name="fargate_task_arn")
