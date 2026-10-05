"""
products.py
------------
CRUD operations, search, and stock-alert logic for the products module.
"""

from database import get_connection
from utils import ValidationError, require_fields, require_number

PRODUCT_SELECT = """
    SELECT p.product_id, p.name, p.category_id, p.price, p.quantity,
           p.description, p.image, p.low_stock_threshold, p.created_at,
           c.name AS category_name
    FROM products p
    LEFT JOIN categories c ON c.category_id = p.category_id
"""


def list_products(category_id=None, search=None):
    conn = get_connection()
    query = PRODUCT_SELECT
    conditions = []
    params = []

    if category_id:
        conditions.append("p.category_id = ?")
        params.append(category_id)
    if search:
        conditions.append("(p.name LIKE ? OR p.description LIKE ?)")
        like = f"%{search}%"
        params.extend([like, like])

    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY p.name ASC"

    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_product(product_id):
    conn = get_connection()
    row = conn.execute(PRODUCT_SELECT + " WHERE p.product_id = ?", (product_id,)).fetchone()
    conn.close()
    if not row:
        raise ValidationError("Product not found.")
    return dict(row)


def create_product(data):
    require_fields(data, ["name", "price", "quantity"])
    name = str(data["name"]).strip()
    if not name:
        raise ValidationError("Product name cannot be empty.")

    price = require_number(data, "price")
    quantity = require_number(data, "quantity")
    if quantity != int(quantity):
        raise ValidationError("Quantity must be a whole number.")
    quantity = int(quantity)

    category_id = data.get("category_id") or None
    description = str(data.get("description", "")).strip()
    image = str(data.get("image", "")).strip()
    low_stock_threshold = int(data.get("low_stock_threshold", 5) or 5)

    conn = get_connection()
    if category_id:
        cat = conn.execute(
            "SELECT category_id FROM categories WHERE category_id = ?",
            (category_id,),
        ).fetchone()
        if not cat:
            conn.close()
            raise ValidationError("Selected category does not exist.")

    cur = conn.execute(
        """INSERT INTO products
           (name, category_id, price, quantity, description, image, low_stock_threshold)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (name, category_id, price, quantity, description, image, low_stock_threshold),
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return get_product(new_id)


def update_product(product_id, data):
    existing = get_product(product_id)  # raises if not found

    name = str(data.get("name", existing["name"])).strip()
    if not name:
        raise ValidationError("Product name cannot be empty.")

    price = data.get("price", existing["price"])
    price = require_number({"price": price}, "price")

    quantity = data.get("quantity", existing["quantity"])
    quantity = require_number({"quantity": quantity}, "quantity")
    if quantity != int(quantity):
        raise ValidationError("Quantity must be a whole number.")
    quantity = int(quantity)

    category_id = data.get("category_id", existing["category_id"]) or None
    description = str(data.get("description", existing["description"] or "")).strip()
    image = str(data.get("image", existing["image"] or "")).strip()
    low_stock_threshold = int(
        data.get("low_stock_threshold", existing["low_stock_threshold"]) or 5
    )

    conn = get_connection()
    if category_id:
        cat = conn.execute(
            "SELECT category_id FROM categories WHERE category_id = ?",
            (category_id,),
        ).fetchone()
        if not cat:
            conn.close()
            raise ValidationError("Selected category does not exist.")

    conn.execute(
        """UPDATE products
           SET name = ?, category_id = ?, price = ?, quantity = ?,
               description = ?, image = ?, low_stock_threshold = ?
           WHERE product_id = ?""",
        (name, category_id, price, quantity, description, image,
         low_stock_threshold, product_id),
    )
    conn.commit()
    conn.close()
    return get_product(product_id)


def delete_product(product_id):
    get_product(product_id)  # raises if not found
    conn = get_connection()
    conn.execute("DELETE FROM products WHERE product_id = ?", (product_id,))
    conn.commit()
    conn.close()
    return {"product_id": product_id, "deleted": True}


def low_stock_products():
    conn = get_connection()
    rows = conn.execute(
        PRODUCT_SELECT + " WHERE p.quantity <= p.low_stock_threshold ORDER BY p.quantity ASC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def check_stock_availability(product_id, requested_qty):
    product = get_product(product_id)
    available = product["quantity"] >= requested_qty
    return {
        "product_id": product_id,
        "requested_qty": requested_qty,
        "available_qty": product["quantity"],
        "in_stock": available,
    }
