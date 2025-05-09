# backend/models.py
import os
import uuid
from decimal import Decimal, InvalidOperation
from boto3.dynamodb.conditions import Key, Attr

import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

# --------------------------------------------------
# Carga de variables de entorno
# --------------------------------------------------
BASE_DIR = os.path.dirname(__file__)
load_dotenv(os.path.join(BASE_DIR, ".env"))

AWS_REGION     = os.getenv("AWS_REGION", "us-east-1")
USERS_TABLE    = os.getenv("USERS_TABLE",  "Usuarios")
PRODUCTS_TABLE = os.getenv("PRODUCTS_TABLE", "Productos")
CART_TABLE     = os.getenv("CART_TABLE",   "Carrito")
ORDERS_TABLE   = os.getenv("ORDERS_TABLE", "Orders")

session  = boto3.Session(
    profile_name=os.getenv("AWS_PROFILE"),   # None → usa variables de entorno / IAM role
    region_name=AWS_REGION
)
dynamodb = session.resource("dynamodb")

users_table    = dynamodb.Table(USERS_TABLE)
products_table = dynamodb.Table(PRODUCTS_TABLE)
cart_table     = dynamodb.Table(CART_TABLE)
orders_table   = dynamodb.Table(ORDERS_TABLE)

# ---------- utilidades ----------
def _decimalize(d: dict) -> dict:
    """Convierte floats a Decimal para DynamoDB"""
    return {k: (Decimal(str(v)) if isinstance(v, (int, float)) else v) for k, v in d.items()}

def _plain(obj):
    """Convierte Decimal → int/float para JSON"""
    if isinstance(obj, list):
        return [_plain(x) for x in obj]
    if isinstance(obj, dict):
        return {k: _plain(v) for k, v in obj.items()}
    if isinstance(obj, Decimal):
        try:
            return int(obj)
        except InvalidOperation:
            return float(obj)
    return obj

# ==================================================
#                     USUARIOS
# ==================================================
def list_users():
    return users_table.scan().get("Items", [])

def create_user(user_id, username, email, password):
    users_table.put_item(Item={
        "user_id":  user_id,
        "username": username,
        "email":    email.lower(),
        "password": password
    })

def update_user(user_id, **fields):
    if not fields:
        return
    expr = "SET " + ", ".join(f"#{k}=:{k}" for k in fields)
    users_table.update_item(
        Key={"user_id": user_id},
        UpdateExpression=expr,
        ExpressionAttributeNames={f"#{k}": k for k in fields},
        ExpressionAttributeValues={f":{k}": v for k, v in fields.items()}
    )

def delete_user(user_id):
    users_table.delete_item(Key={"user_id": user_id})

def verify_user(email, password) -> bool:
    email = email.lower()
    # con GSI email-index si existe, si no, hace scan
    try:
        res = users_table.query(
            IndexName="email-index",
            KeyConditionExpression=boto3.dynamodb.conditions.Key("email").eq(email)
        )
        items = res.get("Items", [])
    except ClientError as e:
        if e.response["Error"]["Code"] == "ValidationException":
            items = users_table.scan(
                FilterExpression=boto3.dynamodb.conditions.Attr("email").eq(email)
            ).get("Items", [])
        else:
            raise
    return bool(items and items[0]["password"] == password)

# ==================================================
#               USUARIO POR CORREO
# ==================================================
def get_user_by_email(email: str):
    """Devuelve el usuario con ese email o None."""
    email = email.lower()
    try:
        res = users_table.query(
            IndexName='email-index',
            KeyConditionExpression=Key('email').eq(email)
        )
        items = res.get('Items', [])
    except ClientError as e:
        if e.response['Error']['Code'] == 'ValidationException':
            items = users_table.scan(
                FilterExpression=Attr('email').eq(email)
            ).get('Items', [])
        else:
            raise
    return items[0] if items else None

# ==================================================
#                    PRODUCTOS
# ==================================================
def create_product(product_id, title, price, stock, img=None):
    item = _decimalize({
        "product_id": product_id,
        "title":      title,
        "price":      price,
        "stock":      stock
    })
    if img:
        item["img"] = img
    products_table.put_item(Item=item)

def list_products():
    return products_table.scan().get("Items", [])

# ---------- PRODUCTOS (edición / borrado) ----------
def update_product(product_id, **fields):
    """
    Actualiza campos del producto (stock, price, title, img …).
    fields se pasa como JSON desde el front; ej. {"stock": 10}
    """
    if not fields:
        return

    update_expr = "SET " + ", ".join(f"#{k}=:{k}" for k in fields)
    names  = {f"#{k}": k for k in fields}
    values = {
        f":{k}": (Decimal(str(v)) if isinstance(v, (int, float)) else v)
        for k, v in fields.items()
    }

    products_table.update_item(
        Key={"product_id": product_id},
        UpdateExpression=update_expr,
        ExpressionAttributeNames=names,
        ExpressionAttributeValues=values
    )

def delete_product(product_id):
    products_table.delete_item(Key={"product_id": product_id})

# ==================================================
#                      CARRITO
# ==================================================
def list_cart(user_id="guest"):
    res = cart_table.query(
        KeyConditionExpression=boto3.dynamodb.conditions.Key("user_id").eq(user_id)
    )
    return res.get("Items", [])

def add_to_cart(product_id, qty=1, user_id="guest"):
    prod = products_table.get_item(Key={"product_id": product_id}).get("Item")
    if not prod:
        return {"error": "Producto no existe"}
    if prod["stock"] < qty:
        return {"error": "Stock insuficiente"}

    # descuenta stock
    products_table.update_item(
        Key={"product_id": product_id},
        UpdateExpression="ADD stock :neg",
        ConditionExpression="stock >= :qty",
        ExpressionAttributeValues={
            ":neg": Decimal(-qty),
            ":qty": Decimal(qty)
        }
    )
    # añade / incrementa en carrito
    cart_table.update_item(
        Key={"user_id": user_id, "product_id": product_id},
        UpdateExpression="SET title=:t, price=:p ADD qty :q",
        ExpressionAttributeValues={
            ":t": prod["title"],
            ":p": prod["price"],
            ":q": Decimal(qty)
        }
    )
    return {"message": "Añadido"}

def remove_from_cart(product_id, user_id="guest"):
    item = cart_table.get_item(Key={"user_id": user_id, "product_id": product_id}).get("Item")
    if item:
        products_table.update_item(
            Key={"product_id": product_id},
            UpdateExpression="ADD stock :q",
            ExpressionAttributeValues={":q": item["qty"]}
        )
    cart_table.delete_item(Key={"user_id": user_id, "product_id": product_id})
    return {"message": "Eliminado"}

# ==================================================
#                       PEDIDOS
# ==================================================
def list_orders():
    return orders_table.scan().get("Items", [])

# ==================================================
#                       CHECKOUT
# ==================================================
def checkout(user_id="guest"):
    items = list_cart(user_id)
    if not items:
        return {"error": "Carrito vacío"}

    order_id = str(uuid.uuid4())
    total = sum(i["price"] * i["qty"] for i in items)

    orders_table.put_item(Item=_decimalize({
        "order_id": order_id,
        "user_id":  user_id,
        "items":    items,
        "total":    total
    }))

    with cart_table.batch_writer() as bw:
        for it in items:
            bw.delete_item(Key={"user_id": user_id, "product_id": it["product_id"]})

    return _plain({"message": "Compra realizada", "order_id": order_id, "total": total})

# ==================================================
#    Crear tablas automáticamente (opcional / local)
# ==================================================
def _ensure_tables():
    existing = {t.name for t in dynamodb.tables.all()}

    def create(name, key_schema, attrs):
        if name in existing:
            return
        dynamodb.create_table(
            TableName=name,
            KeySchema=key_schema,
            AttributeDefinitions=attrs,
            BillingMode="PAY_PER_REQUEST"
        )

    # Usuarios + GSI por email
    if USERS_TABLE not in existing:
        dynamodb.create_table(
            TableName=USERS_TABLE,
            KeySchema=[{"AttributeName": "user_id", "KeyType": "HASH"}],
            AttributeDefinitions=[
                {"AttributeName": "user_id", "AttributeType": "S"},
                {"AttributeName": "email",   "AttributeType": "S"}
            ],
            GlobalSecondaryIndexes=[{
                "IndexName": "email-index",
                "KeySchema": [{"AttributeName": "email", "KeyType": "HASH"}],
                "Projection": {"ProjectionType": "ALL"}
            }],
            BillingMode="PAY_PER_REQUEST"
        )

    create(PRODUCTS_TABLE,
           [{"AttributeName": "product_id", "KeyType": "HASH"}],
           [{"AttributeName": "product_id", "AttributeType": "S"}])

    create(CART_TABLE,
           [{"AttributeName": "user_id",    "KeyType": "HASH"},
            {"AttributeName": "product_id", "KeyType": "RANGE"}],
           [{"AttributeName": "user_id",    "AttributeType": "S"},
            {"AttributeName": "product_id", "AttributeType": "S"}])

    create(ORDERS_TABLE,
           [{"AttributeName": "order_id", "KeyType": "HASH"}],
           [{"AttributeName": "order_id", "AttributeType": "S"}])

# _ensure_tables()   # ← Descomenta si trabajas en local y quieres que las cree
