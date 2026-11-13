import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app.extensions import db
from werkzeug.security import generate_password_hash

def seed_data():
    app = create_app()
    with app.app_context():
        print("Starting database seeding...")

        res_a = db.session.execute(db.text("SELECT id FROM saccos WHERE name = :name"), {"name": "Alpha SACCO"}).fetchone()
        if not res_a:
            db.session.execute(db.text("INSERT INTO saccos (name) VALUES (:name)"), {"name": "Alpha SACCO"})
            db.session.commit()
            res_a = db.session.execute(db.text("SELECT id FROM saccos WHERE name = :name"), {"name": "Alpha SACCO"}).fetchone()
        sacco1_id = res_a[0]

        res_b = db.session.execute(db.text("SELECT id FROM saccos WHERE name = :name"), {"name": "Beta SACCO"}).fetchone()
        if not res_b:
            db.session.execute(db.text("INSERT INTO saccos (name) VALUES (:name)"), {"name": "Beta SACCO"})
            db.session.commit()
            res_b = db.session.execute(db.text("SELECT id FROM saccos WHERE name = :name"), {"name": "Beta SACCO"}).fetchone()
        sacco2_id = res_b[0]

        def upsert_user(email, password, role, sacco_id=None):
            user_res = db.session.execute(db.text("SELECT id FROM users WHERE email = :email"), {"email": email}).fetchone()
            if not user_res:
                hashed_pw = generate_password_hash(password)
                try:
                    db.session.execute(
                        db.text("INSERT INTO users (email, password_hash, role, sacco_id) VALUES (:email, :pw, :role, :sacco_id)"),
                        {"email": email, "pw": hashed_pw, "role": role, "sacco_id": sacco_id}
                    )
                except Exception:
                    db.session.rollback()
                    db.session.execute(
                        db.text("INSERT INTO users (email, password, role, sacco_id) VALUES (:email, :pw, :role, :sacco_id)"),
                        {"email": email, "pw": hashed_pw, "role": role, "sacco_id": sacco_id}
                    )
                db.session.commit()

        upsert_user("owner@nexora.com", "SecureOwner123!", "platform_owner", None)
        upsert_user("admin@alpha.com", "AdminAlpha123!", "sacco_admin", sacco1_id)
        upsert_user("member@alpha.com", "MemberAlpha123!", "member", sacco1_id)

        print("Database seeding completed successfully.")

if __name__ == "__main__":
    seed_data()
