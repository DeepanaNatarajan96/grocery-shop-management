"""
orders.py
---------
Handles checkout (cart -> order -> bill), order history, and bill retrieval.

Business flow:
  1. Frontend cart (held in browser localStorage) is POSTed as a list of
     {product_id, quantity} items, plus an optional customer_id / new
     customer details.
  2. Server validates stock, computes subtotal/tax/total, creates an
     order + order_items, deducts stock, and generates a bill row.
  3. Everything happens inside a single SQLite transaction so partial
     checkouts never corrupt stock counts.
"""

from database import get_connection
from utils import ValidationError, require_fields

TAX_RATE = 0.05          # 5% GST-style tax, adjustable
DISCOUNT_THRESHOLD = 1000  # flat discount kicks in above this subtotal
FLAT_DISCOUNT = 50


def _get_or_create_customer(conn, data):
    """Resolve a customer_id from either an existing id or new customer info."""
    customer_id = data.get("customer_id")
    if customer_id:
        row = conn.execute(
            "SELECT customer_id FROM customers WHERE customer_id = ?",
            (customer_id,),
        ).fetchone()
        if not row:
            raise ValidationError("Selected customer does not exist.")
        return customer_id

    customer = data.get("customer")
    if customer and customer.get("name") and customer.get("phone"):
        existing = conn.execute(
            "SELECT customer_id FROM customers WHERE phone = ?",
            (customer["phone"],),
        ).fetchone()
        if existing:
            return existing["customer_id"]
        cur = conn.execute(
            "INSERT INTO customers (name, phone, email, address) VALUES (?, ?, ?, ?)",
            (
                customer["name"].strip(),
                customer["phone"].strip(),
                customer.get("email", "").strip(),
                customer.get("address", "").strip(),
            ),
        )
        return cur.lastrowid

    return None  # Walk-in / guest checkout allowed


def checkout(data):
    """Create an order + bill from a cart payload. Returns the full bill."""
    require_fields(data, ["items"])
    items = data["items"]
    if not isinstance(items, list) or len(items) == 0:
        raise ValidationError("Cart is empty. Add items before checkout.")

    conn = get_connection()
    try:
        conn.execute("BEGIN")

        customer_id = _get_or_create_customer(conn, data)

        order_items = []
        subtotal = 0.0

        for raw_item in items:
            product_id = raw_item.get("product_id")
            qty = raw_item.get("quantity")
            if not product_id or not qty or int(qty) <= 0:
                raise ValidationError("Each cart item needs a valid product_id and quantity.")
            qty = int(qty)

            product = conn.execute(
                "SELECT * FROM products WHERE product_id = ?", (product_id,)
            ).fetchone()
            if not product:
                raise ValidationError(f"Product ID {product_id} does not exist.")
            if product["quantity"] < qty:
                raise ValidationError(
                    f"Insufficient stock for '{product['name']}'. "
                    f"Available: {product['quantity']}, requested: {qty}."
                )

            line_subtotal = round(product["price"] * qty, 2)
            subtotal += line_subtotal
            order_items.append(
                {
                    "product_id": product_id,
                    "product_name": product["name"],
                    "unit_price": product["price"],
                    "quantity": qty,
                    "subtotal": line_subtotal,
                }
            )

        subtotal = round(subtotal, 2)
        tax = round(subtotal * TAX_RATE, 2)
        discount = FLAT_DISCOUNT if subtotal >= DISCOUNT_THRESHOLD else 0
        total = round(subtotal + tax - discount, 2)

        cur = conn.execute(
            """INSERT INTO orders (customer_id, total_amount, status)
               VALUES (?, ?, 'COMPLETED')""",
            (customer_id, total),
        )
        order_id = cur.lastrowid

        for item in order_items:
            conn.execute(
                """INSERT INTO order_items
                   (order_id, product_id, product_name, unit_price, quantity, subtotal)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    order_id,
                    item["product_id"],
                    item["product_name"],
                    item["unit_price"],
                    item["quantity"],
                    item["subtotal"],
                ),
            )
            conn.execute(
                "UPDATE products SET quantity = quantity - ? WHERE product_id = ?",
                (item["quantity"], item["product_id"]),
            )

        cur = conn.execute(
            """INSERT INTO bills (order_id, subtotal, tax, discount, total_amount)
               VALUES (?, ?, ?, ?, ?)""",
            (order_id, subtotal, tax, discount, total),
        )
        bill_id = cur.lastrowid

        conn.commit()
    except ValidationError:
        conn.rollback()
        raise
    except Exception as exc:  # pragma: no cover - defensive catch-all
        conn.rollback()
        raise ValidationError(f"Checkout failed: {exc}")
    finally:
        conn.close()

    return get_bill(bill_id)


def get_bill(bill_id):
    conn = get_connection()
    bill = conn.execute(
        "SELECT * FROM bills WHERE bill_id = ?", (bill_id,)
    ).fetchone()
    if not bill:
        conn.close()
        raise ValidationError("Bill not found.")

    order = conn.execute(
        "SELECT * FROM orders WHERE order_id = ?", (bill["order_id"],)
    ).fetchone()

    customer = None
    if order["customer_id"]:
        customer = conn.execute(
            "SELECT * FROM customers WHERE customer_id = ?", (order["customer_id"],)
        ).fetchone()

    items = conn.execute(
        "SELECT * FROM order_items WHERE order_id = ?", (order["order_id"],)
    ).fetchall()
    conn.close()

    return {
        "bill_id": bill["bill_id"],
        "bill_date": bill["bill_date"],
        "order_id": order["order_id"],
        "order_date": order["order_date"],
        "customer": dict(customer) if customer else None,
        "items": [dict(i) for i in items],
        "subtotal": bill["subtotal"],
        "tax": bill["tax"],
        "discount": bill["discount"],
        "total_amount": bill["total_amount"],
    }


def list_orders(customer_id=None):
    conn = get_connection()
    query = """
        SELECT o.order_id, o.order_date, o.total_amount, o.status,
               c.name AS customer_name, c.phone AS customer_phone,
               b.bill_id
        FROM orders o
        LEFT JOIN customers c ON c.customer_id = o.customer_id
        LEFT JOIN bills b ON b.order_id = o.order_id
    """
    params = []
    if customer_id:
        query += " WHERE o.customer_id = ?"
        params.append(customer_id)
    query += " ORDER BY o.order_date DESC"

    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_order_detail(order_id):
    conn = get_connection()
    order = conn.execute(
        "SELECT * FROM orders WHERE order_id = ?", (order_id,)
    ).fetchone()
    if not order:
        conn.close()
        raise ValidationError("Order not found.")
    items = conn.execute(
        "SELECT * FROM order_items WHERE order_id = ?", (order_id,)
    ).fetchall()
    bill = conn.execute(
        "SELECT * FROM bills WHERE order_id = ?", (order_id,)
    ).fetchone()
    conn.close()
    return {
        "order": dict(order),
        "items": [dict(i) for i in items],
        "bill": dict(bill) if bill else None,
    }


def sales_report():
    """Aggregate sales figures for a simple report dashboard."""
    conn = get_connection()

    totals = conn.execute(
        """SELECT COUNT(*) AS total_orders,
                  COALESCE(SUM(total_amount), 0) AS total_revenue
           FROM orders"""
    ).fetchone()

    today = conn.execute(
        """SELECT COUNT(*) AS orders_today,
                  COALESCE(SUM(total_amount), 0) AS revenue_today
           FROM orders WHERE date(order_date) = date('now')"""
    ).fetchone()

    top_products = conn.execute(
        """SELECT product_name, SUM(quantity) AS units_sold,
                  SUM(subtotal) AS revenue
           FROM order_items
           GROUP BY product_name
           ORDER BY units_sold DESC
           LIMIT 5"""
    ).fetchall()

    daily_sales = conn.execute(
        """SELECT date(order_date) AS day, SUM(total_amount) AS revenue,
                  COUNT(*) AS orders
           FROM orders
           GROUP BY date(order_date)
           ORDER BY day DESC
           LIMIT 7"""
    ).fetchall()

    conn.close()
    return {
        "total_orders": totals["total_orders"],
        "total_revenue": round(totals["total_revenue"], 2),
        "orders_today": today["orders_today"],
        "revenue_today": round(today["revenue_today"], 2),
        "top_products": [dict(r) for r in top_products],
        "daily_sales": [dict(r) for r in daily_sales],
    }
