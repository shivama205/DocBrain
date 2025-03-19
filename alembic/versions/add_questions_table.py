"""add questions table

Revision ID: add_questions_table
Revises: 18b3efd07130
Create Date: 2024-03-19 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_questions_table'
down_revision = '18b3efd07130'
branch_labels = None
depends_on = None

def upgrade():
    # Create enum types
    op.execute("CREATE TYPE answer_type AS ENUM ('DIRECT', 'SQL_QUERY')")
    op.execute("CREATE TYPE question_status AS ENUM ('PENDING', 'INGESTING', 'COMPLETED', 'FAILED')")

    # Create questions table
    op.create_table(
        'questions',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('question', sa.Text(), nullable=False),
        sa.Column('answer', sa.Text(), nullable=False),
        sa.Column('answer_type', postgresql.ENUM('DIRECT', 'SQL_QUERY', name='answer_type'), nullable=False),
        sa.Column('status', postgresql.ENUM('PENDING', 'INGESTING', 'COMPLETED', 'FAILED', name='question_status'), nullable=False),
        sa.Column('knowledge_base_id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['knowledge_base_id'], ['knowledge_bases.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes
    op.create_index('idx_questions_kb', 'questions', ['knowledge_base_id'])
    op.create_index('idx_questions_user', 'questions', ['user_id'])

def downgrade():
    # Drop indexes
    op.drop_index('idx_questions_user')
    op.drop_index('idx_questions_kb')

    # Drop table
    op.drop_table('questions')

    # Drop enum types
    op.execute('DROP TYPE question_status')
    op.execute('DROP TYPE answer_type') 