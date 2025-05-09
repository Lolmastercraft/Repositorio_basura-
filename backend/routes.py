# backend/routes.py
import os
import uuid
from flask import Blueprint, request, jsonify, session
import models

api = Blueprint("api", __name__, url_prefix="/api")

# =====================================================
#                    AUTENTICACIÓN
# =====================================================
@api.route("/login", methods=["POST"])
def login():
    data  = request.get_json()
    email = data["email"].lower()
    pwd   = data["password"]

    if (email == os.getenv("ADMIN_EMAIL", "admin@vinilos.com").lower()
            and pwd == os.getenv("ADMIN_PASS", "superAdmin123")):
        session.permanent = True
        session["user"]   = {"email": email, "is_admin": True}
        return jsonify({"message": "Admin OK", "is_admin": True})

    if not models.verify_user(email, pwd):
        return jsonify({"error": "Credenciales inválidas"}), 401

    session.permanent = True
    session["user"]   = {"email": email, "is_admin": False}
    return jsonify({"message": "Login OK", "is_admin": False})

@api.route("/logout")
def logout():
    session.clear()
    return jsonify({"message": "Bye"})

@api.route("/me")
def me():
    return jsonify(session.get("user") or {})

# =====================================================
#                     USUARIOS
# =====================================================
@api.route("/users", methods=["GET"])
def list_users():
    return jsonify(models.list_users())

@api.route("/users", methods=["POST"])
def registrar_usuario():
    data  = request.get_json()
    email = data["email"].lower()
    # 1) validamos que NO exista
    if models.get_user_by_email(email):
        return jsonify({"error": "El correo ya está registrado"}), 400

    # 2) creamos usuario nuevo
    user_id = str(uuid.uuid4())
    models.create_user(
        user_id,
        data["username"],
        email,
        data["password"]
    )
    return jsonify({"message": "Usuario creado", "user_id": user_id}), 201

@api.route("/users/<user_id>", methods=["PUT", "DELETE"])
def usuario_crud(user_id):
    if request.method == "PUT":
        models.update_user(user_id, **request.get_json())
        return jsonify({"message": "Actualizado"})
    models.delete_user(user_id)
    return jsonify({"message": "Eliminado"})

# =====================================================
#                     PRODUCTOS
# =====================================================
@api.route("/products", methods=["GET"])
def listar_productos():
    return jsonify(models.list_products())

@api.route("/products", methods=["POST"])
def crear_producto():
    if not session.get("user", {}).get("is_admin"):
        return jsonify({"error": "No autorizado"}), 403
    data = request.get_json()
    models.create_product(
        data["product_id"], data["title"],
        float(data["price"]), int(data["stock"]),
        data.get("img")
    )
    return jsonify({"message": "Producto creado"}), 201

# ---------- PRODUCTO EDIT / DELETE ----------
@api.route('/products/<product_id>', methods=['PUT', 'DELETE'])
def producto_edit(product_id):
    if not session.get('user', {}).get('is_admin'):
        return jsonify({'error': 'No autorizado'}), 403
    if request.method == 'PUT':
        models.update_product(product_id, **request.get_json())
        return jsonify({'message': 'Actualizado'})
    models.delete_product(product_id)
    return jsonify({'message': 'Eliminado'})

# =====================================================
#                       CARRITO
# =====================================================
@api.route("/cart", methods=["GET", "POST"])
def carrito():
    if request.method == "GET":
        return jsonify(models.list_cart())
    data = request.get_json()
    res  = models.add_to_cart(data["product_id"], data.get("qty", 1))
    status = 400 if "error" in res else 201
    return jsonify(res), status

@api.route("/cart/<product_id>", methods=["DELETE"])
def eliminar_del_carrito(product_id):
    return jsonify(models.remove_from_cart(product_id))

# =====================================================
#                       CHECKOUT
# =====================================================
@api.route("/checkout", methods=["POST"])
def realizar_compra():
    res = models.checkout()
    status = 400 if "error" in res else 201
    return jsonify(res), status

# =====================================================
#                       ORDENES
# =====================================================
@api.route('/orders')
def orders():
    if not session.get('user', {}).get('is_admin'):
        return jsonify({'error': 'No autorizado'}), 403
    return jsonify(models.list_orders())
