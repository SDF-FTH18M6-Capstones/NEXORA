import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app.extensions import db
from werkzeug.security import generate_password_hash
from datetime import datetime

def seed_data():
    app = create_app()
    with app.app_context():
        print("Starting database seeding...")

        # 1. Insert/Find Saccos safely
        res_a = db.session.execute(db.text("SELECT id FROM saccos WHERE name = :name"), {"name": "Alpha SACCO"}).fetchone()
        if not res_a:
            db.session.execute(
                db.text("INSERT INTO saccos (name, created_at) VALUES (:name, :created_at)"),
                {"name": "Alpha SACCO", "created_at": datetime.utcnow()}
            )
            db.session.commit()
            res_a = db.session.execute(db.text("SELECT id FROM saccos WHERE name = :name"), {"name": "Alpha SACCO"}).fetchone()
        sacco1_id = res_a[0]

        res_b = db.session.execute(db.text("SELECT id FROM saccos WHERE name = :name"), {"name": "Beta SACCO"}).fetchone()
        if not res_b:
            db.session.execute(
                db.text("INSERT INTO saccos (name, created_at) VALUES (:name, :created_at)"),
                {"name": "Beta SACCO", "created_at": datetime.utcnow()}
            )
            db.session.commit()
            res_b = db.session.execute(db.text("SELECT id FROM saccos WHERE name = :name"), {"name": "Beta SACCO"}).fetchone()
        sacco2_id = res_b[0]

        # 2. Inspect actual columns in the users table
        columns_res = db.session.execute(db.text("SELECT column_name FROM information_schema.columns WHERE table_name = 'users'")).fetchall()
        user_cols = [row[0] for row in columns_res]
        print(f"Detected users table columns: {user_cols}")

        def upsert_user(email, password, role_val=None, sacco_id_val=None):
            user_res = db.session.execute(db.text("SELECT id FROM users WHERE email = :email"), {"email": email}).fetchone()
            if not user_res:
                hashed_pw = generate_password_hash(password)
                
                fields = ["email"]
                params = {"email": email, "pw": hashed_pw}

                pw_col = "password_hash" if "password_hash" in user_cols else ("password" if "password" in user_cols else None)
                if pw_col:
                    fields.append(pw_col)

                if "role" in user_cols and role_val is not None:
                    fields.append("role")
                    params["role"] = role_val

                if "sacco_id" in user_cols and sacco_id_val is not None:
                    fields.append("sacco_id")
                    params["sacco_id"] = sacco_id_val

                if "created_at" in user_cols:
                    fields.append("created_at")
                    params["created_at"] = datetime.utcnow()

                col_names = ", ".join(fields)
                sql_str = f"INSERT INTO users ({col_names}) VALUES (" + ", ".join([(":pw" if f == pw_col else f":{f}") for f in fields]) + ")"
                
                db.session.execute(db.text(sql_str), params)
                db.session.commit()

        upsert_user("owner@nexora.com", "SecureOwner123!", "platform_owner", None)
        upsert_user("admin@alpha.com", "AdminAlpha123!", "sacco_admin", sacco1_id)
        upsert_user("member@alpha.com", "MemberAlpha123!", "member", sacco1_id)

        print("Database seeding completed successfully.")

if __name__ == "__main__":
    seed_data()
