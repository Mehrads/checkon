"""Our own test account on the live site: a complimentary plan with no Stripe subscription behind it, for trying
every paid feature (infra/README.md, "A test account").

    python -m app.test_account you+checkon-test@example.com                  # Agency
    python -m app.test_account you+checkon-test@example.com --plan starter
    python -m app.test_account you+checkon-test@example.com --end            # switch it off

A new user gets the "set your password" email, as after Checkout, and then signs in like any customer: email,
password and the emailed code. The plan's checks apply as usual, but nothing is billed and its checks are left
out of the usage stats. A user who pays through Stripe is never turned into a test account.
"""

import argparse
import logging
import secrets

from pydantic import EmailStr, TypeAdapter, ValidationError
from sqlmodel import Session, func, select

from app.api.billing import plans
from app.api.stripe_webhook import send_set_password_email
from app.core.db import engine
from app.core.security import get_password_hash
from app.models import Customer, User

logger = logging.getLogger(__name__)

_email = TypeAdapter(EmailStr)


class Refused(Exception):
    """The email can't be a test account."""


def _user(session: Session, email: str) -> User | None:
    return session.exec(select(User).where(func.lower(User.email) == email.lower())).first()


def make_test_account(session: Session, email: str, plan: str = "agency") -> tuple[User, Customer, bool]:
    """The test account for this email, created or switched to `plan`; True when the user is new."""
    try:
        email = _email.validate_python(email.strip().lower())
    except ValidationError:
        raise Refused(f"{email!r} isn't an email address.")
    if plan not in plans():
        raise Refused(f"{plan!r} isn't a plan: use one of {', '.join(plans())}.")
    user = _user(session, email)
    created = user is None
    if user is None:
        user = User(email=email, hashed_password=get_password_hash(secrets.token_urlsafe(32)))
    if user.is_superuser:
        raise Refused(f"{email} is an admin; use another address for the test account.")
    customer = session.get(Customer, user.customer_id) if user.customer_id else None
    if customer is not None and not customer.complimentary:
        raise Refused(f"{email} pays through Stripe; a paying account is never turned into a test account.")
    if customer is None:
        customer = Customer(email=email, complimentary=True)
        session.add(customer)
        session.flush()
        user.customer_id = customer.id
    customer.plan = plan
    customer.subscription_status = "active"
    customer.cancel_at_period_end = False
    session.add_all([customer, user])
    session.commit()
    session.refresh(customer)
    return user, customer, created


def end_test_account(session: Session, email: str) -> Customer:
    """Switch the test account off: its plan ends, as a cancelled subscription would. Its history stays."""
    user = _user(session, email)
    customer = session.get(Customer, user.customer_id) if user and user.customer_id else None
    if customer is None or not customer.complimentary:
        raise Refused(f"{email} has no test account.")
    customer.subscription_status = "canceled"
    session.add(customer)
    session.commit()
    return customer


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("email")
    parser.add_argument("--plan", choices=list(plans()), default="agency")
    parser.add_argument("--end", action="store_true", help="switch the test account off")
    args = parser.parse_args()
    with Session(engine) as session:
        try:
            if args.end:
                end_test_account(session, args.email)
                logger.info("The test account for %s is off. Run this again without --end to switch it on.", args.email)
                return
            user, _, created = make_test_account(session, args.email, args.plan)
            address = user.email
        except Refused as error:
            raise SystemExit(str(error))
    plan = plans()[args.plan]
    logger.info("Test account %s: %s plan, complimentary, nothing billed.", address, plan.name)
    if created:
        send_set_password_email(address, plan.name)
        logger.info("New user: the set-password email went to %s (or use Forgot password).", address)


if __name__ == "__main__":
    main()
