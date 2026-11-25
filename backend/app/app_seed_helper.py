"""Helper to seed database safely during test and startup."""

from sqlalchemy.orm import Session
from app.seed_data import seed_caravan_opportunities


def seed_test_database(db: Session) -> int:
    return seed_caravan_opportunities(db)
