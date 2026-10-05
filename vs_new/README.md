# GreenBasket — Grocery Shop Management System

A full-stack Grocery Shop Management System built with **plain HTML/CSS/JavaScript**
on the frontend, a **framework-free Python backend** (`http.server` + `sqlite3`),
and a **SQLite** database. No Flask, Django, React, Bootstrap, or any other
framework is used anywhere in this project.

## Features

- **Admin authentication** — login/logout with hashed passwords and
  server-side session tokens; the admin panel is fully gated behind login.
- **Home page** — hero banner, live stats, featured products, category shortcuts.
- **Product management** — create, edit, delete, and browse products with
  category, price, quantity, description, and a stock/low-stock badge.
- **Category management** — create, edit, delete categories; deleting a
  category safely un-links its products instead of deleting them.
- **Shopping cart** — add/remove/update quantities, running subtotal, tax,
  and discount, all persisted in the browser (`localStorage`) until checkout.
- **Billing system** — checkout validates live stock against SQLite,
  deducts stock, creates an order + bill in one transaction, and shows a
  printable-style receipt.
- **Customer management** — add, edit, delete, and search customers by
  name/phone/email; checkout also auto-creates/matches a customer record.
- **Admin panel** (`admin.html`) — tabbed dashboard for Products,
  Categories, Customers, Orders (with bill viewer), and a Sales Report
  (today's revenue, all-time revenue, top products, last 7 days).
- **Extras** — product search, stock availability checks, low-stock
  alerts, order history, and a sales report endpoint.

## Technology Stack

| Layer     | Technology                                   |
|-----------|-----------------------------------------------|
| Frontend  | HTML5, CSS3 (custom design system), vanilla JS |
| Backend   | Python 3 standard library (`http.server`, `sqlite3`) — **no framework** |
| Database  | SQLite (file-based, auto-created on first run) |

## Project Structure

```
grocery_shop_management_system/
├── start.sh               # One-click start (macOS/Linux)
├── start_windows.bat      # One-click start (Windows)
├── backend/
│   ├── server.py         # HTTP server + routing (the entry point)
│   ├── database.py       # Schema creation + seed data
│   ├── auth.py           # Login/logout, password hashing, sessions
│   ├── utils.py          # JSON helpers, validation helpers
│   ├── products.py       # Product CRUD + stock logic
│   ├── categories.py     # Category CRUD
│   ├── customers.py      # Customer CRUD + search
│   └── orders.py         # Checkout, billing, order history, sales report
├── frontend/
│   ├── index.html        # Home page
│   ├── products.html     # Product catalog with search/filter/sort
│   ├── categories.html   # Category browser
│   ├── cart.html         # Cart + checkout + receipt
│   ├── contact.html      # Contact page
│   ├── login.html        # Admin login
│   ├── admin.html        # Admin panel (all management modules)
│   ├── css/style.css     # Shared design system
│   └── js/
│       ├── main.js       # API client, auth, cart state, header/footer, toasts
│       ├── home.js       # Home page logic
│       ├── products.js   # Product listing logic
│       ├── cart.js       # Cart + checkout logic
│       └── admin.js      # Admin panel logic
├── database/
│   └── grocery.db        # Created automatically on first run
└── README.md
```

## Admin Login

The admin panel (`admin.html`) requires login. A default account is
seeded automatically the first time the server runs:

```
Username: admin
Password: admin123
```

Log in at **http://localhost:8000/login.html** (or click **Admin Login**
in the site header). You can change the password from inside the admin
panel (**🔑 Change Password** button) — this immediately logs out all
active sessions for that account, so you'll need to log in again with
the new password.

Sessions are server-side tokens stored in SQLite (`sessions` table),
valid for 12 hours, sent by the frontend as
`Authorization: Bearer <token>`. Public storefront pages (Home,
Products, Categories, Cart checkout) never require login — only the
admin panel's management endpoints (product/category/customer CRUD,
order history, sales reports) do.

## Getting Started

**Requirements:** Python 3.8+ (no `pip install` needed — everything is
standard library).

**Easiest way:**
- **Windows:** double-click `start_windows.bat`
- **macOS / Linux:** double-click `start.sh`, or run `sh start.sh` in a terminal

**Manual way (any OS):**
```bash
cd grocery_shop_management_system/backend
python server.py
# if "python" isn't recognized, try:  python3 server.py
```

Then open your browser at:

```
http://localhost:8000/
```

> ⚠️ **Important:** open that URL in your browser — don't just
> double-click `index.html`. Opening the HTML file directly (as a
> `file://` link) skips the Python server entirely, so the product
> list, cart, and admin panel can't load any data. The site itself
> will show a red banner if it detects this and tell you what to do.

If port 8000 is already being used by something else, the server will
tell you clearly instead of failing silently — either close the other
program or change `PORT` near the top of `backend/server.py`.

The SQLite database (`database/grocery.db`) is created automatically the
first time the server runs, pre-seeded with sample categories and products
so the site is immediately browsable. Admin management (add/edit/delete)
is available at **http://localhost:8000/admin.html** — see **Admin Login**
above for the default credentials.

To reset all data, stop the server and delete `database/grocery.db`, then
restart — it will be recreated and reseeded automatically.

## API Overview

All endpoints are under `/api` and return JSON in the shape
`{ "success": true, "data": ... }` or `{ "success": false, "error": "..." }`.

| Method | Endpoint                          | Description                          |
|--------|------------------------------------|---------------------------------------|
| POST   | `/api/login`                      | Log in, returns a session token       |
| POST   | `/api/logout`                     | Invalidate the current session token  |
| GET    | `/api/session`                    | Get the logged-in user for a token    |
| POST   | `/api/change-password`            | Change password (requires login)      |
| GET    | `/api/products`                   | List products (`?category_id=`, `?search=`) |
| GET    | `/api/products/{id}`              | Get one product                       |
| POST   | `/api/products`                   | Create product                        |
| PUT    | `/api/products/{id}`              | Update product                        |
| DELETE | `/api/products/{id}`              | Delete product                        |
| GET    | `/api/products-low-stock`         | List products at/under their threshold |
| GET    | `/api/products/{id}/stock-check`  | Check stock for a requested quantity  |
| GET    | `/api/categories`                 | List categories                       |
| POST   | `/api/categories`                 | Create category                       |
| PUT    | `/api/categories/{id}`            | Update category                       |
| DELETE | `/api/categories/{id}`            | Delete category                       |
| GET    | `/api/customers`                  | List/search customers (`?search=`)    |
| POST   | `/api/customers`                  | Create customer                       |
| PUT    | `/api/customers/{id}`             | Update customer                       |
| DELETE | `/api/customers/{id}`             | Delete customer                       |
| POST   | `/api/checkout`                   | Convert a cart into an order + bill   |
| GET    | `/api/orders`                     | Order history (`?customer_id=`)       |
| GET    | `/api/orders/{id}`                | Order detail with items + bill        |
| GET    | `/api/bills/{id}`                 | Bill/receipt detail                   |
| GET    | `/api/reports/sales`              | Sales report (totals, top products, 7-day trend) |

> Routes that create/update/delete data, plus all `/api/customers`,
> `/api/orders`, `/api/reports/sales`, and `/api/products-low-stock`,
> require a valid `Authorization: Bearer <token>` header from
> `/api/login`. `/api/checkout` and all `GET` product/category listing
> routes stay public for the storefront.

## Design Notes

- **Billing math:** subtotal → +5% tax → -₹50 flat discount on subtotals
  ≥ ₹1000 → total. Adjustable in `backend/orders.py` (`TAX_RATE`,
  `DISCOUNT_THRESHOLD`, `FLAT_DISCOUNT`) and mirrored in `frontend/js/cart.js`
  for the live on-page summary (the server always recalculates and is the
  source of truth at checkout).
- **Stock integrity:** checkout runs inside a single SQLite transaction —
  stock is only deducted if every line item has sufficient quantity, so
  partial/broken orders can't corrupt inventory counts.
- **Low-stock alerts:** each product has a `low_stock_threshold` (default 5);
  the admin dashboard and `/api/products-low-stock` surface anything at or
  below that threshold.
