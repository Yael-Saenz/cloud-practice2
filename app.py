import os
import sqlite3
from datetime import datetime

from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

DB_PATH = "catalog.db"
API_KEY = os.environ.get("API_KEY", "devkey")


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            stock INTEGER NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def check_api_key():
    return request.headers.get("X-API-KEY") == API_KEY


@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "time": datetime.now().isoformat()
    })


@app.route("/products", methods=["GET"])
def get_products():
    if not check_api_key():
        return jsonify({"error": "unauthorized"}), 401

    conn = get_db_connection()
    products = conn.execute(
        "SELECT id, name, price, stock FROM products"
    ).fetchall()
    conn.close()

    return jsonify([dict(product) for product in products])


@app.route("/products", methods=["POST"])
def create_product():
    if not check_api_key():
        return jsonify({"error": "unauthorized"}), 401

    data = request.get_json()

    if not data or "name" not in data or "price" not in data or "stock" not in data:
        return jsonify({
            "error": "name, price and stock are required"
        }), 400

    conn = get_db_connection()
    cursor = conn.execute(
        "INSERT INTO products (name, price, stock) VALUES (?, ?, ?)",
        (data["name"], data["price"], data["stock"])
    )
    conn.commit()

    product = {
        "id": cursor.lastrowid,
        "name": data["name"],
        "price": data["price"],
        "stock": data["stock"]
    }

    conn.close()
    return jsonify(product), 201


@app.route("/products/<int:product_id>", methods=["GET"])
def get_product(product_id):
    if not check_api_key():
        return jsonify({"error": "unauthorized"}), 401

    conn = get_db_connection()
    product = conn.execute(
        "SELECT id, name, price, stock FROM products WHERE id = ?",
        (product_id,)
    ).fetchone()
    conn.close()

    if product is None:
        return jsonify({"error": "product not found"}), 404

    return jsonify(dict(product))


@app.route("/products/<int:product_id>", methods=["PUT"])
def update_product(product_id):
    if not check_api_key():
        return jsonify({"error": "unauthorized"}), 401

    data = request.get_json()

    if not data:
        return jsonify({"error": "JSON body is required"}), 400

    conn = get_db_connection()
    product = conn.execute(
        "SELECT id, name, price, stock FROM products WHERE id = ?",
        (product_id,)
    ).fetchone()

    if product is None:
        conn.close()
        return jsonify({"error": "product not found"}), 404

    name = data.get("name", product["name"])
    price = data.get("price", product["price"])
    stock = data.get("stock", product["stock"])

    conn.execute(
        "UPDATE products SET name = ?, price = ?, stock = ? WHERE id = ?",
        (name, price, stock, product_id)
    )
    conn.commit()
    conn.close()

    return jsonify({
        "id": product_id,
        "name": name,
        "price": price,
        "stock": stock
    })


@app.route("/products/<int:product_id>", methods=["DELETE"])
def delete_product(product_id):
    if not check_api_key():
        return jsonify({"error": "unauthorized"}), 401

    conn = get_db_connection()

    cursor = conn.execute(
        "DELETE FROM products WHERE id = ?",
        (product_id,)
    )

    conn.commit()
    deleted = cursor.rowcount
    conn.close()

    if deleted == 0:
        return jsonify({"error": "product not found"}), 404

    return jsonify({"deleted": product_id}), 200
      
if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=8080, debug=True)