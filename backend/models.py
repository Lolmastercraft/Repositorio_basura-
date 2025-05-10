"""
models.py  – Capa de acceso a DynamoDB
"""

from __future__ import annotations
import os
from decimal import Decimal
import uuid
from datetime import datetime
import boto3
from boto3.dynamodb.conditions import Key

# ---------------------------------------------------------------------------
# 1. CONEXIÓN A DYNAMODB
# ---------------------------------------------------------------------------
_SESSION = boto3.session.Session(
    profile_name=os.getenv("AWS_PROFILE") or None  # ➊ Usa perfil local solo fuera de AWS
)
dynamodb = _SESSION.resource(
    "dynamodb",
    region_name=os.getenv("AWS_REGION", "us-east-1")
)

TABLE_USERS    = dynamodb.Table(os.getenv("USERS_TABLE",    "users"))
TABLE_PRODUCTS = dynamodb.Table(os.getenv("PRODUCTS_TABLE", "products"))
TABLE_CART     = dynamodb.Table(os.getenv("CART_TABLE",     "carts"))
TABLE_ORDERS   = dynamodb.Table(os.getenv("ORDERS_TABLE",   "orders"))

# ---------------------------------------------------------------------------
# 2. UTILIDADES PARA CONVERSIÓN DECIMAL ↔ JSON
# ---------------------------------------------------------------------------
def _to_decimal(obj):
    """Convierte float → Decimal para que DynamoDB lo acepte."""
    if isinstance(obj, float):
        return Decimal(str(obj))
    if isinstance(obj, dict):
        return {k: _to_decimal(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_to_decimal(v) for v in obj]
    return obj

def _from_decimal(obj):
    """Convierte Decimal → int/float para consumir en JSON."""
    if isinstance(obj, Decimal):
        return int(obj) if obj % 1 == 0 else float(obj)
    if isinstance(obj, dict):
        return {k: _from_decimal(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_from_decimal(v) for v in obj]
    return obj

# ---------------------------------------------------------------------------
# 3. CRUD USUARIOS
# ---------------------------------------------------------------------------
def create_user(username: str, password: str, role: str = "user") -> dict:
    item = _to_decimal({
        "id": str(uuid.uuid4()),
        "username": username,
        "password": password,
        "role": role,
        "created_at": datetime.utcnow().isoformat()
    })
    TABLE_USERS.put_item(Item=item)
    return _from_decimal(item)

def get_user(user_id: str) -> dict | None:
    res = TABLE_USERS.get_item(Key={"id": user_id})
    return _from_decimal(res["Item"]) if "Item" in res else None

def get_user_by_username(username: str) -> dict | None:
    """
    Busca por GSI username-index (crea un GSI si aún no existe) para login.
    """
    res = TABLE_USERS.query(
        IndexName="username-index",
        KeyConditionExpression=Key("username").eq(username)
    )
    return _from_decimal(res["Items"][0]) if res["Items"] else None

def delete_user(user_id: str) -> None:
    TABLE_USERS.delete_item(Key={"id": user_id})

def user_exists(user_id: str) -> bool:
    """Lectura directa para saber si sigue existiendo."""
    return TABLE_USERS.get_item(Key={"id": user_id}).get("Item") is not None

# ---------------------------------------------------------------------------
# 4. CRUD PRODUCTOS
# ---------------------------------------------------------------------------
def list_products() -> list[dict]:
    res = TABLE_PRODUCTS.scan()
    return _from_decimal(res.get("Items", []))

def create_product(name: str, price: float, stock: int) -> dict:
    item = _to_decimal({
        "id": str(uuid.uuid4()),
        "name": name,
        "price": price,
        "stock": stock,
        "created_at": datetime.utcnow().isoformat()
    })
    TABLE_PRODUCTS.put_item(Item=item)
    return _from_decimal(item)

def update_product(product_id: str, attrs: dict) -> dict:
    """Actualiza solo los atributos recibidos."""
    expr_attrs = {f":{k}": _to_decimal(v) for k, v in attrs.items()}
    update_expr = "SET " + ", ".join(f"{k}=:{k}" for k in attrs.keys())
    TABLE_PRODUCTS.update_item(
        Key={"id": product_id},
        UpdateExpression=update_expr,
        ExpressionAttributeValues=expr_attrs
    )
    return get_product(product_id)

def get_product(product_id: str) -> dict | None:
    res = TABLE_PRODUCTS.get_item(Key={"id": product_id})
    return _from_decimal(res["Item"]) if "Item" in res else None

# ---------------------------------------------------------------------------
# 5. CARRITO
# ---------------------------------------------------------------------------
def add_to_cart(user_id: str, product_id: str, quantity: int) -> dict:
    item = _to_decimal({
        "user_id": user_id,
        "product_id": product_id,
        "quantity": quantity,
        "added_at": datetime.utcnow().isoformat()
    })
    TABLE_CART.put_item(Item=item)
    return _from_decimal(item)

def list_cart(user_id: str) -> list[dict]:
    res = TABLE_CART.query(
        KeyConditionExpression=Key("user_id").eq(user_id)
    )
    return _from_decimal(res.get("Items", []))

def clear_cart(user_id: str) -> None:
    items = list_cart(user_id)
    with TABLE_CART.batch_writer() as batch:
        for it in items:
            batch.delete_item(Key={"user_id": user_id, "product_id": it["product_id"]})

# ---------------------------------------------------------------------------
# 6. ÓRDENES
# ---------------------------------------------------------------------------
def create_order(user_id: str, items: list[dict], total: float) -> dict:
    order = _to_decimal({
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "items": items,
        "total": total,
        "created_at": datetime.utcnow().isoformat()
    })
    TABLE_ORDERS.put_item(Item=order)
    # limpiar carrito
    clear_cart(user_id)
    return _from_decimal(order)

def list_orders(user_id: str) -> list[dict]:
    res = TABLE_ORDERS.query(
        IndexName="user_id-index",
        KeyConditionExpression=Key("user_id").eq(user_id)
    )
    return _from_decimal(res.get("Items", []))
