"""Create tasks table

Revision ID: 96aa4169751a
Revises:
Create Date: 2025-03-11 13:24:34.747381

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "96aa4169751a"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "tasks",
        sa.Column("task_id", sa.String(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("PENDING", "IN_PROGRESS", "SUCCESS", "FAILED", name="taskstatus"),
            nullable=True,
        ),
        sa.Column("file_path", sa.String(), nullable=True),
        sa.Column("results", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("task_id"),
    )
    op.create_index(op.f("ix_tasks_task_id"), "tasks", ["task_id"], unique=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f("ix_tasks_task_id"), table_name="tasks")
    op.drop_table("tasks")
    # ### end Alembic commands ###
