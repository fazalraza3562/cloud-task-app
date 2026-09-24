import os

import psycopg
from flask import Flask, jsonify, request
from psycopg.errors import UniqueViolation
from psycopg.rows import dict_row

app = Flask(__name__)


def get_db_connection():
    return psycopg.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        dbname=os.getenv("DB_NAME", "cloudtasks"),
        user=os.getenv("DB_USER", "clouduser"),
        password=os.getenv("DB_PASSWORD"),
        row_factory=dict_row
    )


def init_db():
    conn = get_db_connection()

    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    email VARCHAR(255) UNIQUE NOT NULL
                );
            """)
        conn.commit()
    finally:
        conn.close()


@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "service": "User Service",
        "message": "User Service is running"
    })


@app.route("/health", methods=["GET"])
def health():
    try:
        conn = get_db_connection()

        with conn.cursor() as cur:
            cur.execute("SELECT 1;")

        conn.close()

        return jsonify({
            "status": "healthy",
            "service": "user-service",
            "database": "connected"
        }), 200

    except Exception:
        return jsonify({
            "status": "unhealthy",
            "service": "user-service",
            "database": "unavailable"
        }), 503


@app.route("/api/users", methods=["GET"])
def get_users():
    conn = get_db_connection()

    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, name, email
                FROM users
                ORDER BY id;
            """)
            users = cur.fetchall()

        return jsonify(users), 200
    finally:
        conn.close()


@app.route("/api/users/<int:user_id>", methods=["GET"])
def get_user(user_id):
    conn = get_db_connection()

    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, name, email
                FROM users
                WHERE id = %s;
            """, (user_id,))
            user = cur.fetchone()

        if user is None:
            return jsonify({"error": "User not found"}), 404

        return jsonify(user), 200
    finally:
        conn.close()


@app.route("/api/users", methods=["POST"])
def create_user():
    data = request.get_json()

    if not data:
        return jsonify({"error": "JSON body is required"}), 400

    name = data.get("name")
    email = data.get("email")

    if not name or not email:
        return jsonify({
            "error": "Both name and email are required"
        }), 400

    conn = get_db_connection()

    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO users (name, email)
                VALUES (%s, %s)
                RETURNING id, name, email;
            """, (name, email))

            user = cur.fetchone()

        conn.commit()
        return jsonify(user), 201

    except UniqueViolation:
        conn.rollback()

        return jsonify({
            "error": "A user with this email already exists"
        }), 409

    finally:
        conn.close()


@app.route("/api/users/<int:user_id>", methods=["PUT"])
def update_user(user_id):
    data = request.get_json()

    if not data:
        return jsonify({"error": "JSON body is required"}), 400

    conn = get_db_connection()

    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, name, email
                FROM users
                WHERE id = %s;
            """, (user_id,))

            existing_user = cur.fetchone()

            if existing_user is None:
                return jsonify({"error": "User not found"}), 404

            new_name = data.get("name", existing_user["name"])
            new_email = data.get("email", existing_user["email"])

            cur.execute("""
                UPDATE users
                SET name = %s, email = %s
                WHERE id = %s
                RETURNING id, name, email;
            """, (new_name, new_email, user_id))

            updated_user = cur.fetchone()

        conn.commit()
        return jsonify(updated_user), 200

    except UniqueViolation:
        conn.rollback()

        return jsonify({
            "error": "A user with this email already exists"
        }), 409

    finally:
        conn.close()


@app.route("/api/users/<int:user_id>", methods=["DELETE"])
def delete_user(user_id):
    conn = get_db_connection()

    try:
        with conn.cursor() as cur:
            cur.execute("""
                DELETE FROM users
                WHERE id = %s
                RETURNING id;
            """, (user_id,))

            deleted_user = cur.fetchone()

        if deleted_user is None:
            conn.rollback()
            return jsonify({"error": "User not found"}), 404

        conn.commit()

        return jsonify({
            "message": "User deleted successfully"
        }), 200

    finally:
        conn.close()


if __name__ == "__main__":
    init_db()

    app.run(
        host="0.0.0.0",
        port=5001,
        debug=True
    )
