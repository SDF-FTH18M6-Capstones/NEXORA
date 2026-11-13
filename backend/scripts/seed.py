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

        sacco1 = Sacco.query.filter_by(name="Alpha SACCO").first()
        if not sacco1:
            sacco1 = Sacco(name="Alpha SACCO", is_active=True)
            db.session.add(sacco1)

        sacco2 = Sacco.query.filter_by(name="Beta SACCO").first()
        if not sacco2:
            sacco2 = Sacco(name="Beta SACCO", is_active=True)
            db.session.add(sacco2)
        
        db.session.commit()

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
                sacco_id=sacco1.id
            )
            db.session.add(admin_a)

        member_a = User.query.filter_by(email="member@alpha.com").first()
        if not member_a:
            member_a = User(
                email="member@alpha.com",
                password_hash=generate_password_hash("MemberAlpha123!"),
                role="member",
                sacco_id=sacco1.id
            )
            db.session.add(member_a)

        db.session.commit()
        print("Database seeding completed successfully.")

if __name__ == "__main__":
    seed_data()
