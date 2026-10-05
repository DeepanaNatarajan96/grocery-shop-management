"""
customers.py
------------
CRUD and search operations for the customers module.
"""

import re
import sqlite3
from database import get_connection
from utils import ValidationError, require_fields

PHONE_RE = re.compile(r"^[0-9+\-\s]{7,15}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def list_customers():
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM customers ORDER BY name ASC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_customer(customer_id):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM customers WHERE customer_id = ?", (customer_id,)
    ).fetchone()
    conn.close()
    if not row:
        raise ValidationError("Customer not found.")
    return dict(row)


def search_customers(query):
    conn = get_connection()
    like = f"%{query}%"
    rows = conn.execute(
        """SELECT * FROM customers
           WHERE name LIKE ? OR phone LIKE ? OR email LIKE ?
           ORDER BY name ASC""",
        (like, like, like),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def create_customer(data):
    require_fields(data, ["name", "phone"])
    name = str(data["name"]).strip()
    phone = str(data["phone"]).strip()
    email = str(data.get("email", "")).strip()
    address = str(data.get("address", "")).strip()

    if not name:
        raise ValidationError("Customer name cannot be empty.")
    if not PHONE_RE.match(phone):
        raise ValidationError("Enter a valid phone number.")
    if email and not EMAIL_RE.match(email):
        raise ValidationError("Enter a valid email address.")

    conn = get_connection()
    try:
        cur = conn.execute(
            "INSERT INTO customers (name, phone, email, address) VALUES (?, ?, ?, ?)",
            (name, phone, email, address),
        )
        conn.commit()
        new_id = cur.lastrowid
    except sqlite3.IntegrityError:
        conn.close()
        raise ValidationError(f"A customer with phone '{phone}' already exists.")
    conn.close()
    return get_customer(new_id)


def update_customer(customer_id, data):
    existing = get_customer(customer_id)  # raises if not found

    name = str(data.get("name", existing["name"])).strip()
    phone = str(data.get("phone", existing["phone"])).strip()
    email = str(data.get("email", existing["email"] or "")).strip()
    address = str(data.get("address", existing["address"] or "")).strip()

    if not name:
        raise ValidationError("Customer name cannot be empty.")
    if not PHONE_RE.match(phone):
        raise ValidationError("Enter a valid phone number.")
    if email and not EMAIL_RE.match(email):
        raise ValidationError("Enter a valid email address.")

    conn = get_connection()
    try:
        conn.execute(
            """UPDATE customers SET name = ?, phone = ?, email = ?, address = ?
               WHERE customer_id = ?""",
            (name, phone, email, address, customer_id),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        raise ValidationError(f"A customer with phone '{phone}' already exists.")
    conn.close()
    return get_customer(customer_id)


def delete_customer(customer_id):
    get_customer(customer_id)  # raises if not found
    conn = get_connection()
    conn.execute("DELETE FROM customers WHERE customer_id = ?", (customer_id,))
    conn.commit()
    conn.close()
    return {"customer_id": customer_id, "deleted": True}
