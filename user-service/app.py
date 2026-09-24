from flask import Flask, jsonify, request

app = Flask(__name__)

# Temporary in-memory storage.
# We will replace this with PostgreSQL later.
users = []
next_user_id = 1


@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "service": "User Service",
        "message": "User Service is running"
    })


@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "healthy",
        "service": "user-service"
    }), 200


@app.route("/api/users", methods=["GET"])
def get_users():
    return jsonify(users), 200


@app.route("/api/users/<int:user_id>", methods=["GET"])
def get_user(user_id):
    user = next((user for user in users if user["id"] == user_id), None)

    if user is None:
        return jsonify({"error": "User not found"}), 404

    return jsonify(user), 200


@app.route("/api/users", methods=["POST"])
def create_user():
    global next_user_id

    data = request.get_json()

    if not data:
        return jsonify({"error": "JSON body is required"}), 400

    name = data.get("name")
    email = data.get("email")

    if not name or not email:
        return jsonify({
            "error": "Both name and email are required"
        }), 400

    user = {
        "id": next_user_id,
        "name": name,
        "email": email
    }

    users.append(user)
    next_user_id += 1

    return jsonify(user), 201


@app.route("/api/users/<int:user_id>", methods=["PUT"])
def update_user(user_id):
    user = next((user for user in users if user["id"] == user_id), None)

    if user is None:
        return jsonify({"error": "User not found"}), 404

    data = request.get_json()

    if not data:
        return jsonify({"error": "JSON body is required"}), 400

    if "name" in data:
        user["name"] = data["name"]

    if "email" in data:
        user["email"] = data["email"]

    return jsonify(user), 200


@app.route("/api/users/<int:user_id>", methods=["DELETE"])
def delete_user(user_id):
    global users

    user = next((user for user in users if user["id"] == user_id), None)

    if user is None:
        return jsonify({"error": "User not found"}), 404

    users = [user for user in users if user["id"] != user_id]

    return jsonify({
        "message": "User deleted successfully"
    }), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
