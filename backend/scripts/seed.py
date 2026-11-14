"""Seed a development database with demo SACCOs, users and money movements.

Run from the repo root:  python backend/scripts/seed.py

Safe to run twice: users and SACCOs are looked up first, accounts are opened
only when missing, and every deposit, withdrawal and reversal uses a fixed
reference, which the services treat as a replay. Everything goes through the
models and services, so the ledger, balances and audit rows stay consistent.
"""

import os
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

# One clearly fake password for every seeded user (dev databases only).
DEV_PASSWORD = "Dev-Seed-Pass-2026"
DOMAIN = "example.com"
OWNER_EMAIL = f"owner@{DOMAIN}"

SACCOS = (("Alpha SACCO", "alpha"), ("Beta SACCO", "beta"))

# Amounts are integers in minor units (100 = 1.00).
MOVEMENTS = {
    1: (("deposit", 5000), ("deposit", 2000), ("withdraw", 1000)),
    2: (("deposit", 3000), ("withdraw", 500)),
    3: (("deposit", 1500),),
}


def load_env(path=BACKEND / ".env"):
    """Load backend/.env into the environment. Config reads it at import time."""
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.removeprefix("export ").strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        os.environ.setdefault(key, value)


def require_dev_database(app):
    from sqlalchemy.engine import make_url

    name = make_url(app.config["SQLALCHEMY_DATABASE_URI"]).database or ""
    if not name.endswith("_dev"):
        raise SystemExit(
            f"Refusing to seed database {name!r}: its name must end in '_dev'. "
            "The seed writes demo users with a known password, so it only "
            "runs against a development database."
        )


def seed(app, require_dev=True):
    """Create the demo data and return [{email, role, sacco}, ...]."""
    from sqlalchemy import func, select

    from datetime import UTC, datetime

    from app.auth.passwords import hash_password, validate_password
    from app.extensions import db
    from app.ledger import reversals
    from app.models.ledger import Transaction
    from app.models.membership import MembershipRole, SaccoMembership
    from app.models.sacco import Sacco
    from app.models.savings import SavingsAccount
    from app.models.user import User
    from app.savings import service

    if require_dev:
        require_dev_database(app)

    emails = [OWNER_EMAIL]
    for _, slug in SACCOS:
        emails += [f"{slug}-admin@{DOMAIN}", f"{slug}-staff@{DOMAIN}"]
        emails += [f"{slug}-m{i}@{DOMAIN}" for i in MOVEMENTS]
    for email in emails:
        problem = validate_password(DEV_PASSWORD, email)
        if problem:
            raise SystemExit(f"DEV_PASSWORD is not valid for {email}: {problem}")

    def get_user(email, owner=False):
        user = db.session.execute(
            select(User).where(func.lower(User.email) == email.lower())
        ).scalar_one_or_none()
        if user is None:
            user = User(
                email=email,
                password_hash=hash_password(DEV_PASSWORD),
                is_platform_owner=owner,
                email_verified_at=datetime.now(UTC),
            )
            db.session.add(user)
            db.session.flush()
            user_id = user.id
            db.session.commit()
            return user_id
        return user.id

    def get_sacco(name):
        sacco = db.session.execute(
            select(Sacco).where(func.lower(Sacco.name) == name.lower())
        ).scalar_one_or_none()
        if sacco is None:
            sacco = Sacco(name=name)
            db.session.add(sacco)
            db.session.flush()
            sacco_id = sacco.id
            db.session.commit()
            return sacco_id
        return sacco.id

    def get_membership(user_id, sacco_id, role):
        found = db.session.execute(
            select(SaccoMembership).where(
                SaccoMembership.user_id == user_id,
                SaccoMembership.sacco_id == sacco_id,
            )
        ).scalar_one_or_none()
        if found is None:
            found = SaccoMembership(user_id=user_id, sacco_id=sacco_id, role=role)
            db.session.add(found)
            db.session.flush()
            membership_id = found.id
            db.session.commit()
            return membership_id
        return found.id

    def get_account(admin_id, membership_id):
        account_id = db.session.execute(
            select(SavingsAccount.id).where(
                SavingsAccount.membership_id == membership_id
            )
        ).scalar_one_or_none()
        if account_id is None:
            account_id = service.open_account(admin_id, membership_id).id
        return account_id

    seeded = []
    with app.app_context():
        get_user(OWNER_EMAIL, owner=True)
        seeded.append({"email": OWNER_EMAIL, "role": "platform_owner", "sacco": None})

        for name, slug in SACCOS:
            sacco_id = get_sacco(name)

            admin_email = f"{slug}-admin@{DOMAIN}"
            admin_id = get_user(admin_email)
            get_membership(admin_id, sacco_id, MembershipRole.SACCO_ADMIN)
            seeded.append({"email": admin_email, "role": "sacco_admin", "sacco": name})

            staff_email = f"{slug}-staff@{DOMAIN}"
            staff_id = get_user(staff_email)
            get_membership(staff_id, sacco_id, MembershipRole.STAFF)
            seeded.append({"email": staff_email, "role": "staff", "sacco": name})

            for i, moves in MOVEMENTS.items():
                email = f"{slug}-m{i}@{DOMAIN}"
                user_id = get_user(email)
                membership_id = get_membership(user_id, sacco_id, MembershipRole.MEMBER)
                seeded.append({"email": email, "role": "member", "sacco": name})

                account_id = get_account(admin_id, membership_id)
                done = {"deposit": 0, "withdraw": 0}
                for kind, amount in moves:
                    done[kind] += 1
                    short = "dep" if kind == "deposit" else "wd"
                    reference = f"seed-{slug}-m{i}-{short}-{done[kind]}"
                    getattr(service, kind)(admin_id, account_id, amount, reference)

            # One reversal: undo the second deposit of the first member.
            original = db.session.execute(
                select(Transaction).where(
                    Transaction.sacco_id == sacco_id,
                    Transaction.reference == f"seed-{slug}-m1-dep-2",
                )
            ).scalar_one()
            reversals.reverse_transaction(
                admin_id, original.id, f"seed-{slug}-m1-rev-1"
            )

        db.session.remove()
    return seeded


def main():
    load_env()
    from app import create_app

    app = create_app()
    seeded = seed(app)
    print(f"Seeded. Every user's password is: {DEV_PASSWORD}\n")
    for row in seeded:
        where = row["sacco"] or "-"
        print(f"  {row['email']:<28} {row['role']:<15} {where}")


if __name__ == "__main__":
    main()
