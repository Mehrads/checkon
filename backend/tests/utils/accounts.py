import secrets
from datetime import timedelta

from sqlmodel import Session

from app.core import security
from app.models import Customer, User


def make_customer(db: Session) -> Customer:
    """An account, as app/api/accounts.py makes one on a user's first signed-in request."""
    customer = Customer(email=f"{secrets.token_hex(6)}@agency.example")
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


def make_user(db: Session, customer: Customer | None = None) -> tuple[User, dict[str, str]]:
    user = User(email=f"{secrets.token_hex(6)}@agency.example", hashed_password="x",
                customer_id=customer.id if customer else None)  # fmt: skip
    db.add(user)
    db.commit()
    db.refresh(user)
    token = security.create_access_token(user.id, expires_delta=timedelta(minutes=5))
    return user, {"Authorization": f"Bearer {token}"}
