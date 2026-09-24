import os

import psycopg
import requests
from flask import Flask, jsonify, request
from psycopg.rows import dict_row

app = Flask(__name__)

USER_SERVICE_URL = os.getenv(
    "USER_SERVICE_URL",
    "http://localhost:5001"
)


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
                CREATE TABLE IF NOT EXISTS tasks (
                    id SERIAL PRIMARY KEY,
                    title VARCHAR(255) NOT NULL,
                    completed BOOLEAN NOT NULL DEFAULT FALSE,
                    user_id INTEGER NOT NULL
                );
            """)

        conn.commit()
    finally:
        conn.close()


@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "service": "Task Service",
        "message": "Task Service is running"
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
            "service": "task-service",
            "database": "connected"
        }), 200

    except Exception:
        return jsonify({
            "status": "unhealthy",
            "service": "task-service",
            "database": "unavailable"
        }), 503


@app.route("/api/tasks", methods=["GET"])
def get_tasks():
    conn = get_db_connection()

    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, title, completed, user_id
                FROM tasks
                ORDER BY id;
            """)

            tasks = cur.fetchall()

        return jsonify(tasks), 200
    finally:
        conn.close()


@app.route("/api/tasks/<int:task_id>", methods=["GET"])
def get_task(task_id):
    conn = get_db_connection()

    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, title, completed, user_id
                FROM tasks
                WHERE id = %s;
            """, (task_id,))

            task = cur.fetchone()

        if task is None:
            return jsonify({
                "error": "Task not found"
            }), 404

        return jsonify(task), 200
    finally:
        conn.close()


@app.route("/api/tasks", methods=["POST"])
def create_task():
    data = request.get_json()

    if not data:
        return jsonify({
            "error": "JSON body is required"
        }), 400

    title = data.get("title")
    user_id = data.get("user_id")

    if not title or user_id is None:
        return jsonify({
            "error": "title and user_id are required"
        }), 400

    # REST call to User Service.
    try:
        response = requests.get(
            f"{USER_SERVICE_URL}/api/users/{user_id}",
            timeout=5
        )
    except requests.RequestException:
        return jsonify({
            "error": "User Service is unavailable"
        }), 503

    if response.status_code == 404:
        return jsonify({
            "error": "Assigned user does not exist"
        }), 400

    if response.status_code != 200:
        return jsonify({
            "error": "Unable to verify assigned user"
        }), 502

    user = response.json()

    conn = get_db_connection()

    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO tasks (
                    title,
                    completed,
                    user_id
                )
                VALUES (%s, %s, %s)
                RETURNING id, title, completed, user_id;
            """, (
                title,
                False,
                user_id
            ))

            task = cur.fetchone()

        conn.commit()

        task["assigned_user"] = user["name"]

        return jsonify(task), 201

    finally:
        conn.close()


@app.route("/api/tasks/<int:task_id>", methods=["PUT"])
def update_task(task_id):
    data = request.get_json()

    if not data:
        return jsonify({
            "error": "JSON body is required"
        }), 400

    conn = get_db_connection()

    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, title, completed, user_id
                FROM tasks
                WHERE id = %s;
            """, (task_id,))

            existing_task = cur.fetchone()

            if existing_task is None:
                return jsonify({
                    "error": "Task not found"
                }), 404

            new_title = data.get(
                "title",
                existing_task["title"]
            )

            new_completed = data.get(
                "completed",
                existing_task["completed"]
            )

            cur.execute("""
                UPDATE tasks
                SET title = %s,
                    completed = %s
                WHERE id = %s
                RETURNING id, title, completed, user_id;
            """, (
                new_title,
                new_completed,
                task_id
            ))

            updated_task = cur.fetchone()

        conn.commit()

        return jsonify(updated_task), 200

    finally:
        conn.close()


@app.route("/api/tasks/<int:task_id>", methods=["DELETE"])
def delete_task(task_id):
    conn = get_db_connection()

    try:
        with conn.cursor() as cur:
            cur.execute("""
                DELETE FROM tasks
                WHERE id = %s
                RETURNING id;
            """, (task_id,))

            deleted_task = cur.fetchone()

        if deleted_task is None:
            conn.rollback()

            return jsonify({
                "error": "Task not found"
            }), 404

        conn.commit()

        return jsonify({
            "message": "Task deleted successfully"
        }), 200

    finally:
        conn.close()


if __name__ == "__main__":
    init_db()

    app.run(
        host="0.0.0.0",
        port=5002,
        debug=True
    )
