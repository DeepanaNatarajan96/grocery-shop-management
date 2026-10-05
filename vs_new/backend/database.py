"""
database.py
------------
Handles SQLite database connection, schema creation, and seed data
for the Grocery Shop Management System.

No ORM / framework is used - plain sqlite3 (Python standard library).
"""

import sqlite3
import os

# Database file lives in the /database folder at project root
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "database", "grocery.db")


def get_connection():
    """Return a new SQLite connection with foreign keys enabled."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create all required tables if they do not already exist."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_connection()
    cur = conn.cursor()

    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS categories (
            category_id   INTEGER PRIMARY KEY AUTOINCREMENT,
            name          TEXT NOT NULL UNIQUE,
            description   TEXT
        );

        CREATE TABLE IF NOT EXISTS products (
            product_id    INTEGER PRIMARY KEY AUTOINCREMENT,
            name          TEXT NOT NULL,
            category_id   INTEGER,
            price         REAL NOT NULL CHECK (price >= 0),
            quantity      INTEGER NOT NULL DEFAULT 0 CHECK (quantity >= 0),
            description   TEXT,
            image         TEXT DEFAULT '',
            low_stock_threshold INTEGER NOT NULL DEFAULT 5,
            created_at    TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (category_id) REFERENCES categories(category_id)
                ON DELETE SET NULL
        );

        CREATE TABLE IF NOT EXISTS customers (
            customer_id   INTEGER PRIMARY KEY AUTOINCREMENT,
            name          TEXT NOT NULL,
            phone         TEXT NOT NULL UNIQUE,
            email         TEXT,
            address       TEXT,
            created_at    TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS orders (
            order_id      INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id   INTEGER,
            order_date    TEXT DEFAULT (datetime('now')),
            total_amount  REAL NOT NULL DEFAULT 0,
            status        TEXT NOT NULL DEFAULT 'COMPLETED',
            FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
                ON DELETE SET NULL
        );

        CREATE TABLE IF NOT EXISTS order_items (
            item_id       INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id      INTEGER NOT NULL,
            product_id    INTEGER,
            product_name  TEXT NOT NULL,
            unit_price    REAL NOT NULL,
            quantity      INTEGER NOT NULL,
            subtotal      REAL NOT NULL,
            FOREIGN KEY (order_id) REFERENCES orders(order_id)
                ON DELETE CASCADE,
            FOREIGN KEY (product_id) REFERENCES products(product_id)
                ON DELETE SET NULL
        );

        CREATE TABLE IF NOT EXISTS bills (
            bill_id       INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id      INTEGER NOT NULL UNIQUE,
            bill_date     TEXT DEFAULT (datetime('now')),
            subtotal      REAL NOT NULL,
            tax           REAL NOT NULL,
            discount      REAL NOT NULL DEFAULT 0,
            total_amount  REAL NOT NULL,
            FOREIGN KEY (order_id) REFERENCES orders(order_id)
                ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS users (
            user_id       INTEGER PRIMARY KEY AUTOINCREMENT,
            username      TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            full_name     TEXT,
            role          TEXT NOT NULL DEFAULT 'admin',
            created_at    TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS sessions (
            token         TEXT PRIMARY KEY,
            user_id       INTEGER NOT NULL,
            created_at    TEXT DEFAULT (datetime('now')),
            expires_at    TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
                ON DELETE CASCADE
        );
        """
    )
    conn.commit()

    # Seed categories & products only if the database is empty,
    # so re-running the server never duplicates data.
    cur.execute("SELECT COUNT(*) AS c FROM categories")
    if cur.fetchone()["c"] == 0:
        _seed_data(conn)

    conn.close()


def _seed_data(conn):
    """Insert a small starter catalog so the app is usable immediately."""
    cur = conn.cursor()

    categories = [
        ("Fruits & Vegetables", "Fresh farm produce"),
        ("Dairy & Eggs", "Milk, cheese, curd, eggs and more"),
        ("Bakery", "Bread, buns, cakes and pastries"),
        ("Beverages", "Juices, soft drinks, tea and coffee"),
        ("Snacks", "Chips, biscuits and namkeen"),
        ("Grains & Staples", "Rice, atta, dal and pulses"),
    ]
    cur.executemany(
        "INSERT INTO categories (name, description) VALUES (?, ?)", categories
    )
    conn.commit()

    cur.execute("SELECT category_id, name FROM categories")
    cat_map = {row["name"]: row["category_id"] for row in cur.fetchall()}

    products = [
        ("Fresh Apples (1 kg)", "Fruits & Vegetables", 180.0, 40, "Crisp red apples", "🍎"),
        ("Bananas (Dozen)", "Fruits & Vegetables", 60.0, 60, "Ripe yellow bananas", "🍌"),
        ("Tomatoes (1 kg)", "Fruits & Vegetables", 40.0, 50, "Farm fresh tomatoes", "🍅"),
        ("Carrots (500 g)", "Fruits & Vegetables", 30.0, 45, "Crunchy orange carrots", "🥕"),
        ("Toned Milk (1 L)", "Dairy & Eggs", 58.0, 70, "Pasteurized toned milk", "🥛"),
        ("Farm Eggs (Tray of 12)", "Dairy & Eggs", 90.0, 35, "Fresh brown eggs", "🥚"),
        ("Paneer (200 g)", "Dairy & Eggs", 85.0, 25, "Soft cottage cheese", "🧀"),
        ("Brown Bread", "Bakery", 45.0, 30, "Whole wheat brown bread", "🍞"),
        ("Butter Croissant", "Bakery", 35.0, 20, "Freshly baked croissant", "🥐"),
        ("Orange Juice (1 L)", "Beverages", 110.0, 30, "100% natural orange juice", "🧃"),
        ("Green Tea (25 bags)", "Beverages", 150.0, 20, "Antioxidant rich green tea", "🍵"),
        ("Potato Chips (Family Pack)", "Snacks", 50.0, 4, "Classic salted chips", "🍟"),
        ("Digestive Biscuits", "Snacks", 40.0, 8, "Wheat digestive biscuits", "🍪"),
        ("Basmati Rice (5 kg)", "Grains & Staples", 480.0, 15, "Premium long-grain rice", "🍚"),
        ("Toor Dal (1 kg)", "Grains & Staples", 140.0, 3, "Split pigeon peas", "🌾"),
        ("Wheat Atta (5 kg)", "Grains & Staples", 220.0, 18, "Whole wheat flour", "🌾"),
    ]
    cur.executemany(
        """INSERT INTO products (name, category_id, price, quantity, description, image)
           VALUES (?, ?, ?, ?, ?, ?)""",
        [(n, cat_map[c], p, q, d, img) for n, c, p, q, d, img in products],
    )
    conn.commit()


if __name__ == "__main__":
    init_db()
    print(f"Database initialized at: {DB_PATH}")
