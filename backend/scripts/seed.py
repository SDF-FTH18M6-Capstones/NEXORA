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

        # 1. SACCOs using raw SQL (inserting only existing columns: name)
        result_a = db.session.execute(db.text("SELECT id FROM saccos WHERE name = :name"), {"name": "Alpha SACCO"}).fetchone()
        if not result_a:
            db.session.execute(db.text("INSERT INTO saccos (name) VALUES (:name)"), {"name": "Alpha SACCO"})
            db.session.commit()
            result_a = db.session.execute(db.text("SELECT id FROM saccos WHERE name = :name"), {"name": "Alpha SACCO"}).fetchone()
        sacco1_id = result_a[0]

        result_b = db.session.execute(db.text("SELECT id FROM saccos WHERE name = :name"), {"name": "Beta SACCO"}).fetchone()
        if not result_b:
            db.session.execute(db.text("INSERT INTO saccos (name) VALUES (:name)"), {"name": "Beta SACCO"})
            db.session.commit()
            result_b = db.session.execute(db.text("SELECT id FROM saccos WHERE name = :name"), {"name": "Beta SACCO"}).fetchone()
        sacco2_id = result_b[0]

        # 2. Users using raw SQL
        owner_res = db.session.execute(db.text("SELECT id FROM users WHERE email = :email"), {"email": "owner@nexora.com"}).fetchone()
        if not owner_res:
            hashed_pw = generate_password_hash("SecureOwner123!")
            try:
                db.session.execute(
                    db.text("INSERT INTO users (email, password_hash, role) VALUES (:email, :pw, :role)"),
                    {"email": "owner@nexora.com", "pw": hashed_pw, "role": "platform_owner"}
                )
            except Exception:
                db.session.rollback()
                db.session.execute(
                    db.text("INSERT INTO users (email, password, role) VALUES (:email, :pw, :role)"),
                    {"email": "owner@nexora.com", "pw": hashed_pw, "role": "platform_owner"}
                )
            db.session.commit()

        admin_res = db.session.execute(db.text("SELECT id FROM users WHERE email = :email"), {"email": "admin@alpha.com"}).fetchone()
        if not admin_res:
            hashed_pw = generate_password_hash("AdminAlpha123!")
            try:
                db.session.execute(
                    db.text("INSERT INTO users (email, password_hash, role, sacco_id) VALUES (:email, :pw, :role, :sacco_id)"),
                    {"email": "admin@alpha.com", "pw": hashed_pw, "role": "sacco_admin", "sacco_id": sacco1_id}
                )
            except Exception:
                db.session.rollback()
                db.session.execute(
                    db.text("INSERT INTO users (email, password, role, sacco_id) VALUES (:email, :pw, :role, :sacco_id)"),
                    {"email": "admin@alpha.com", "pw": hashed_pw, "role": "sacco_admin", "sacco_id": sacco1_id}
                )
            db.session.commit()

        member_res = db.session.execute(db.text("SELECT id FROM users WHERE email = :email"), {"email": "member@alpha.com"}).fetchone()
        if not member_res:
            hashed_pw = generate_password_hash("MemberAlpha123!")
            try:
                db.session.execute(
                    db.text("INSERT INTO users (email, password_hash, role, sacco_id) VALUES (:email, :pw, :role, :sacco_id)"),
                    {"email": "member@alpha.com", "pw": hashed_pw, "role": "member", "sacco_id": sacco1_id}
                )
            except Exception:
                db.session.rollback()
                db.session.execute(
                    db.text("INSERT INTO users (email, password, role, sacco_id) VALUES (:email, :pw, :role, :sacco_id)"),
                    {"email": "member@alpha.com", "pw": hashed_pw, "role": "member", "sacco_id": sacco1_id}
                )
            db.session.commit()

        print("Database seeding completed successfully.")

if __name__ == "__main__":
    seed_data()
