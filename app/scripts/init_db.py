"""Script to initialize the database by creating all tables defined in the models."""

import os
import sys

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import Base, sync_engine
from app.models import *


def init_db():
    """Initialize the database"""
    print("Initializing database...")

    # Create all tables
    Base.metadata.create_all(bind=sync_engine)

    print("Database initialized successfully!")


if __name__ == "__main__":
    init_db()
