import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.sacco import Sacco
from werkzeug.security import generate_password_hash

def seed_data():
    app = create_app()
    with app.app_context():
        print("Starting database seeding...")

        # Use raw SQL or inspect to avoid querying non-existent columns, 
        # or safely check via connection execution if needed.
        # Let's check Sacco existence via raw execute to bypass model attribute mapping mismatches:
        result_a = db.session.execute(db.text("SELECT id FROM saccos WHERE name = :name"), {"name": "Alpha SACCO"}).fetchone()
        if not result_a:
            db.session.execute(db.text("INSERT INTO saccos (name, is_active) VALUES (:name, :active)"), {"name": "Alpha SACCO", "active": True})
            db.session.commit()
            result_a = db.session.execute(db.text("SELECT id FROM saccos WHERE name = :name"), {"name": "Alpha SACCO"}).fetchone()
        sacco1_id = result_a[0]

        result_b = db.session.execute(db.text("SELECT id FROM saccos WHERE name = :name"), {"name": "Beta SACCO"}).fetchone()
        if not result_b:
            db.session.execute(db.text("INSERT INTO saccos (name, is_active) VALUES (:name, :active)"), {"name": "Beta SACCO", "active": True})
            db.session.commit()
            result_b = db.session.execute(db.text("SELECT id FROM saccos WHERE name = :name"), {"name": "Beta SACCO"}).fetchone()
        sacco2_id = result_b[0]

        owner = User.query.filter_by(email="owner@nexora.com").first()
        if not owner:
            owner = User(
                email="owner@nexora.com",
                password_hash=generate_password_hash("SecureOwner123!"),
                role="platform_owner"
            )
            db.session.add(owner)

        admin_a = User.query.filter_by(email="admin@alpha.com").first()
        if not admin_a:
            admin_a = User(
                email="admin@alpha.com",
                password_hash=generate_password_hash("AdminAlpha123!"),
                role="sacco_admin",
                sacco_id=sacco1_id
            )
            db.session.add(admin_a)

        member_a = User.query.filter_by(email="member@alpha.com").first()
        if not member_a:
            member_a = User(
                email="member@alpha.com",
                password_hash=generate_password_hash("MemberAlpha123!"),
                role="member",
                sacco_id=sacco1_id
            )
            db.session.add(member_a)

        db.session.commit()
        print("Database seeding completed successfully.")

if __name__ == "__main__":
    seed_data()
