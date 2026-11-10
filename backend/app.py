import os

import psycopg
from dotenv import load_dotenv
from flask import Flask, jsonify

load_dotenv()

app = Flask(__name__)


@app.get("/api/health")
def health():
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        return jsonify({
            "status": "error",
            "database": "not_configured"
        }), 503

    try:
        with psycopg.connect(database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()

        return jsonify({
            "status": "healthy",
            "database": "connected"
        }), 200

    except psycopg.Error:
        return jsonify({
            "status": "error",
            "database": "disconnected"
        }), 503


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=os.getenv("FLASK_DEBUG") == "1"
    )
