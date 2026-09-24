import os
import requests
from flask import Flask, jsonify, request

app = Flask(__name__)

USER_SERVICE_URL = os.getenv(
    "USER_SERVICE_URL",
    "http://localhost:5001"
)

tasks = []
next_task_id = 1


@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "service": "Task Service",
        "message": "Task Service is running"
    })


@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "healthy",
        "service": "task-service"
    }), 200


@app.route("/api/tasks", methods=["GET"])
def get_tasks():
    return jsonify(tasks), 200


@app.route("/api/tasks/<int:task_id>", methods=["GET"])
def get_task(task_id):
    task = next(
        (task for task in tasks if task["id"] == task_id),
        None
    )

    if task is None:
        return jsonify({"error": "Task not found"}), 404

    return jsonify(task), 200


@app.route("/api/tasks", methods=["POST"])
def create_task():
    global next_task_id

    data = request.get_json()

    if not data:
        return jsonify({"error": "JSON body is required"}), 400

    title = data.get("title")
    user_id = data.get("user_id")

    if not title or user_id is None:
        return jsonify({
            "error": "title and user_id are required"
        }), 400

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

    task = {
        "id": next_task_id,
        "title": title,
        "completed": False,
        "user_id": user_id,
        "assigned_user": user["name"]
    }

    tasks.append(task)
    next_task_id += 1

    return jsonify(task), 201


@app.route("/api/tasks/<int:task_id>", methods=["PUT"])
def update_task(task_id):
    task = next(
        (task for task in tasks if task["id"] == task_id),
        None
    )

    if task is None:
        return jsonify({"error": "Task not found"}), 404

    data = request.get_json()

    if not data:
        return jsonify({"error": "JSON body is required"}), 400

    if "title" in data:
        task["title"] = data["title"]

    if "completed" in data:
        task["completed"] = bool(data["completed"])

    return jsonify(task), 200


@app.route("/api/tasks/<int:task_id>", methods=["DELETE"])
def delete_task(task_id):
    global tasks

    task = next(
        (task for task in tasks if task["id"] == task_id),
        None
    )

    if task is None:
        return jsonify({"error": "Task not found"}), 404

    tasks = [
        task for task in tasks
        if task["id"] != task_id
    ]

    return jsonify({
        "message": "Task deleted successfully"
    }), 200


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5002,
        debug=True
    )
