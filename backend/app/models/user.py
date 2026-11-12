from app.extensions import db
from datetime import datetime, timezone

class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)
    password_hash = db.Column(db.String(255), nullable=False)
    
    # Timezone-aware datetime field matching the lockout checks
    locked_until = db.Column(db.DateTime(timezone=True), nullable=True)

    def __repr__(self):
        return f"<User {self.username}>"