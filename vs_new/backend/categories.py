"""
categories.py
--------------
CRUD operations for the categories module.
"""

import sqlite3
from database import get_connection
from utils import ValidationError, require_fields


def list_categories():
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT c.category_id, c.name, c.description,
               COUNT(p.product_id) AS product_count
        FROM categories c
        LEFT JOIN products p ON p.category_id = c.category_id
        GROUP BY c.category_id
        ORDER BY c.name ASC
        """
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_category(category_id):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM categories WHERE category_id = ?", (category_id,)
    ).fetchone()
    conn.close()
    if not row:
        raise ValidationError("Category not found.")
    return dict(row)


def create_category(data):
    require_fields(data, ["name"])
    name = str(data["name"]).strip()
    description = str(data.get("description", "")).strip()
    if not name:
        raise ValidationError("Category name cannot be empty.")

    conn = get_connection()
    try:
        cur = conn.execute(
            "INSERT INTO categories (name, description) VALUES (?, ?)",
            (name, description),
        )
        conn.commit()
        new_id = cur.lastrowid
    except sqlite3.IntegrityError:
        conn.close()
        raise ValidationError(f"Category '{name}' already exists.")
    conn.close()
    return get_category(new_id)


def update_category(category_id, data):
    conn = get_connection()
    existing = conn.execute(
        "SELECT * FROM categories WHERE category_id = ?", (category_id,)
    ).fetchone()
    if not existing:
        conn.close()
        raise ValidationError("Category not found.")

    name = str(data.get("name", existing["name"])).strip()
    description = str(data.get("description", existing["description"] or "")).strip()

    if not name:
        conn.close()
        raise ValidationError("Category name cannot be empty.")

    try:
        conn.execute(
            "UPDATE categories SET name = ?, description = ? WHERE category_id = ?",
            (name, description, category_id),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        raise ValidationError(f"Category '{name}' already exists.")
    conn.close()
    return get_category(category_id)


def delete_category(category_id):
    conn = get_connection()
    existing = conn.execute(
        "SELECT * FROM categories WHERE category_id = ?", (category_id,)
    ).fetchone()
    if not existing:
        conn.close()
        raise ValidationError("Category not found.")

    # Unlink products instead of blocking deletion (category_id -> NULL)
    conn.execute(
        "UPDATE products SET category_id = NULL WHERE category_id = ?",
        (category_id,),
    )
    conn.execute("DELETE FROM categories WHERE category_id = ?", (category_id,))
    conn.commit()
    conn.close()
    return {"category_id": category_id, "deleted": True}
