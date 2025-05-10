"""
routes.py  – Blueprint con endpoints REST
"""

from __future__ import annotations
from functools import wraps
from flask import Blueprint, request, jsonify, session, abort
from werkzeug.security import generate_password_hash, check_password_hash
import models

api = Blueprint("api", __name__)

# ---------------------------------------------------------------------------
# 1. DECORADOR: login_required_active
# ---------------------------------------------------------------------------
def login_required_active(fn):
    """
    Verifica que session['user_id'] exista y que el usuario siga presente en DynamoDB.
    Aborta con 401 si no es válido.
    """
    @wraps(fn)
    def _wrapper(*args, **kwargs):
        user_id = session.get("user_id")
        if not user_id or not models.user_exists(user_id):
            abort(401, description="Sesión inválida o usuario eliminado")
        return fn(*args, **kwargs)
    return _wrapper


# ---------------------------------------------------------------------------
# 2. NUEVO ENDPOINT  /api/me   (lo pidió el front)
# ---------------------------------------------------------------------------
@api.route("/api/me", methods=["GET"])
def who_am_i():
    """
    Devuelve información básica de la sesión actual:
        { "user_id": "<uuid>|None", "is_admin": true|false }
    Si no hay sesión válida → devuelve user_id: None.
    """
    uid = session.get("user_id")
    if not uid or not models.user_exists(uid):
        return jsonify({"user_id": None, "is_admin": False}), 200

    usr = models.get_user(uid)
    return jsonify({"user_id": uid, "is_admin": usr.get("role") == "admin"}), 200


# ---------------------------------------------------------------------------
# 3. AUTENTICACIÓN
# ---------------------------------------------------------------------------
@api.route("/api/register", methods=["POST"])
def register():
    data = request.json or {}
    if not data.get("username") or not data.get("password"):
        abort(400, description="username y password requeridos")
    if models.get_user_by_username(data["username"]):
        abort(409, description="Usuario ya existe")
    user = models.create_user(
        username=data["username"],
        password=generate_password_hash(data["password"])
    )
    return jsonify(user), 201


@api.route("/api/login", methods=["POST"])
def login():
    data = request.json or {}
    user = models.get_user_by_username(data.get("username", ""))
    if not user or not check_password_hash(user["password"], data.get("password", "")):
        abort(401, description="Credenciales incorrectas")
    session["user_id"] = user["id"]
    return jsonify({"msg": "login ok"}), 200


@api.route("/api/logout", methods=["POST"])
@login_required_active
def logout():
    session.clear()
    return jsonify({"msg": "logout ok"}), 200


# ---------------------------------------------------------------------------
# 4. USUARIOS
# ---------------------------------------------------------------------------
@api.route("/api/users/<user_id>", methods=["DELETE"])
@login_required_active
def delete_user(user_id):
    models.delete_user(user_id)
    # si es su propia sesión, limpiar cookie
    if session.get("user_id") == user_id:
        session.clear()
    return jsonify({"msg": "Usuario eliminado"}), 200


# ---------------------------------------------------------------------------
# 5. PRODUCTOS
# ---------------------------------------------------------------------------
@api.route("/api/products", methods=["GET"])
def products_list():
    return jsonify(models.list_products()), 200


@api.route("/api/products", methods=["POST"])
@login_required_active
def products_create():
    data = request.json or {}
    product = models.create_product(
        name=data.get("name", ""),
        price=float(data.get("price", 0)),
        stock=int(data.get("stock", 0))
    )
    return jsonify(product), 201


@api.route("/api/products/<product_id>", methods=["PATCH"])
@login_required_active
def products_update(product_id):
    data = request.json or {}
    product = models.update_product(product_id, data)
    return jsonify(product), 200


# ---------------------------------------------------------------------------
# 6. CARRITO
# ---------------------------------------------------------------------------
@api.route("/api/cart", methods=["GET"])
@login_required_active
def cart_list():
    return jsonify(models.list_cart(session["user_id"])), 200


@api.route("/api/cart", methods=["POST"])
@login_required_active
def cart_add():
    data = request.json or {}
    item = models.add_to_cart(
        user_id=session["user_id"],
        product_id=data.get("product_id"),
        quantity=int(data.get("quantity", 1))
    )
    return jsonify(item), 201


@api.route("/api/cart/checkout", methods=["POST"])
@login_required_active
def cart_checkout():
    uid = session["user_id"]
    cart_items = models.list_cart(uid)
    if not cart_items:
        abort(400, description="Carrito vacío")

    total = sum(i["quantity"] * models.get_product(i["product_id"])["price"]
                for i in cart_items)
    order = models.create_order(uid, cart_items, total)
    return jsonify(order), 201


# ---------------------------------------------------------------------------
# 7. ÓRDENES
# ---------------------------------------------------------------------------
@api.route("/api/orders", methods=["GET"])
@login_required_active
def orders_list():
    return jsonify(models.list_orders(session["user_id"])), 200


# ---------------------------------------------------------------------------
# 8. PANEL ADMIN (opcional)
# ---------------------------------------------------------------------------
@api.route("/admin", methods=["GET"])
@login_required_active
def admin_panel():
    return "<h1>Panel Admin OK</h1>", 200
