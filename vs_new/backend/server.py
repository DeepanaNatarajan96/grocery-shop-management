"""
server.py
---------
Pure-Python backend for the Grocery Shop Management System.

- No web framework used: built on http.server.BaseHTTPRequestHandler.
- Serves the static frontend (HTML/CSS/JS) from ../frontend
- Exposes a JSON REST-style API under /api/* backed by SQLite.

Run with:  python server.py
Then open: http://localhost:8000/
"""

import os
import sys
import re
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import init_db
from utils import (
    ValidationError,
    json_body_or_400,
    send_success_json,
    send_error_json,
    get_bearer_token,
)
import products as products_module
import categories as categories_module
import customers as customers_module
import orders as orders_module
import auth as auth_module
from auth import AuthError

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")
PORT = 8000

# Route patterns: (method, regex, handler_name)
# Handlers receive (handler, match, query, body)
ID_RE = r"(\d+)"


def route(method, pattern):
    compiled = re.compile(f"^{pattern}$")

    def decorator(func):
        ROUTES.append((method, compiled, func))
        return func

    return decorator


ROUTES = []


def require_login(func):
    """Route decorator: rejects the request with 401 unless a valid
    session token is present in the Authorization header."""
    def wrapper(handler, match, query, body):
        token = get_bearer_token(handler)
        auth_module.get_user_for_token(token)  # raises AuthError if invalid
        return func(handler, match, query, body)
    return wrapper


# -------------------------------------------------------------- Auth
@route("POST", r"/api/login")
def api_login(handler, match, query, body):
    data = auth_module.login(body.get("username"), body.get("password"))
    send_success_json(handler, data)


@route("POST", r"/api/logout")
def api_logout(handler, match, query, body):
    auth_module.logout(get_bearer_token(handler))
    send_success_json(handler, {"logged_out": True})


@route("GET", r"/api/session")
def api_session(handler, match, query, body):
    user = auth_module.get_user_for_token(get_bearer_token(handler))
    send_success_json(handler, user)


@route("POST", r"/api/change-password")
@require_login
def api_change_password(handler, match, query, body):
    user = auth_module.get_user_for_token(get_bearer_token(handler))
    auth_module.change_password(
        user["user_id"], body.get("old_password"), body.get("new_password")
    )
    send_success_json(handler, {"changed": True})


# ---------------------------------------------------------------- Products
@route("GET", r"/api/products")
def api_list_products(handler, match, query, body):
    category_id = query.get("category_id", [None])[0]
    search = query.get("search", [None])[0]
    data = products_module.list_products(category_id=category_id, search=search)
    send_success_json(handler, data)


@route("GET", rf"/api/products/{ID_RE}")
def api_get_product(handler, match, query, body):
    data = products_module.get_product(int(match.group(1)))
    send_success_json(handler, data)


@route("POST", r"/api/products")
@require_login
def api_create_product(handler, match, query, body):
    data = products_module.create_product(body)
    send_success_json(handler, data, status_code=201)


@route("PUT", rf"/api/products/{ID_RE}")
@require_login
def api_update_product(handler, match, query, body):
    data = products_module.update_product(int(match.group(1)), body)
    send_success_json(handler, data)


@route("DELETE", rf"/api/products/{ID_RE}")
@require_login
def api_delete_product(handler, match, query, body):
    data = products_module.delete_product(int(match.group(1)))
    send_success_json(handler, data)


@route("GET", r"/api/products-low-stock")
@require_login
def api_low_stock(handler, match, query, body):
    send_success_json(handler, products_module.low_stock_products())


@route("GET", rf"/api/products/{ID_RE}/stock-check")
def api_stock_check(handler, match, query, body):
    qty = int(query.get("quantity", [1])[0])
    data = products_module.check_stock_availability(int(match.group(1)), qty)
    send_success_json(handler, data)


# --------------------------------------------------------------- Categories
@route("GET", r"/api/categories")
def api_list_categories(handler, match, query, body):
    send_success_json(handler, categories_module.list_categories())


@route("GET", rf"/api/categories/{ID_RE}")
def api_get_category(handler, match, query, body):
    send_success_json(handler, categories_module.get_category(int(match.group(1))))


@route("POST", r"/api/categories")
@require_login
def api_create_category(handler, match, query, body):
    data = categories_module.create_category(body)
    send_success_json(handler, data, status_code=201)


@route("PUT", rf"/api/categories/{ID_RE}")
@require_login
def api_update_category(handler, match, query, body):
    data = categories_module.update_category(int(match.group(1)), body)
    send_success_json(handler, data)


@route("DELETE", rf"/api/categories/{ID_RE}")
@require_login
def api_delete_category(handler, match, query, body):
    data = categories_module.delete_category(int(match.group(1)))
    send_success_json(handler, data)


# --------------------------------------------------------------- Customers
@route("GET", r"/api/customers")
@require_login
def api_list_customers(handler, match, query, body):
    search = query.get("search", [None])[0]
    if search:
        data = customers_module.search_customers(search)
    else:
        data = customers_module.list_customers()
    send_success_json(handler, data)


@route("GET", rf"/api/customers/{ID_RE}")
@require_login
def api_get_customer(handler, match, query, body):
    send_success_json(handler, customers_module.get_customer(int(match.group(1))))


@route("POST", r"/api/customers")
@require_login
def api_create_customer(handler, match, query, body):
    data = customers_module.create_customer(body)
    send_success_json(handler, data, status_code=201)


@route("PUT", rf"/api/customers/{ID_RE}")
@require_login
def api_update_customer(handler, match, query, body):
    data = customers_module.update_customer(int(match.group(1)), body)
    send_success_json(handler, data)


@route("DELETE", rf"/api/customers/{ID_RE}")
@require_login
def api_delete_customer(handler, match, query, body):
    data = customers_module.delete_customer(int(match.group(1)))
    send_success_json(handler, data)


# ------------------------------------------------------------ Orders/Bills
@route("POST", r"/api/checkout")
def api_checkout(handler, match, query, body):
    data = orders_module.checkout(body)
    send_success_json(handler, data, status_code=201)


@route("GET", r"/api/orders")
@require_login
def api_list_orders(handler, match, query, body):
    customer_id = query.get("customer_id", [None])[0]
    send_success_json(handler, orders_module.list_orders(customer_id))


@route("GET", rf"/api/orders/{ID_RE}")
@require_login
def api_get_order(handler, match, query, body):
    send_success_json(handler, orders_module.get_order_detail(int(match.group(1))))


@route("GET", rf"/api/bills/{ID_RE}")
def api_get_bill(handler, match, query, body):
    send_success_json(handler, orders_module.get_bill(int(match.group(1))))


@route("GET", r"/api/reports/sales")
@require_login
def api_sales_report(handler, match, query, body):
    send_success_json(handler, orders_module.sales_report())


# ------------------------------------------------------------------ Server
class GroceryRequestHandler(BaseHTTPRequestHandler):
    server_version = "GroceryShopHTTP/1.0"

    def log_message(self, fmt, *args):
        sys.stderr.write(f"[{self.log_date_time_string()}] {fmt % args}\n")

    # ---- Static file serving -------------------------------------------
    def _serve_static(self, path):
        if path == "/":
            path = "/index.html"
        safe_path = os.path.normpath(path).lstrip(os.sep)
        full_path = os.path.join(FRONTEND_DIR, safe_path)

        # Prevent path traversal outside the frontend directory
        if not os.path.abspath(full_path).startswith(os.path.abspath(FRONTEND_DIR)):
            self.send_error(403, "Forbidden")
            return

        if not os.path.isfile(full_path):
            full_path = os.path.join(FRONTEND_DIR, "index.html")
            if not os.path.isfile(full_path):
                self.send_error(404, "Not Found")
                return

        mime_type, _ = mimetypes.guess_type(full_path)
        mime_type = mime_type or "application/octet-stream"

        with open(full_path, "rb") as f:
            content = f.read()

        self.send_response(200)
        self.send_header("Content-Type", mime_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    # ---- Routing ----------------------------------------------------------
    def _dispatch(self, method):
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        if not path.startswith("/api/"):
            if method == "GET":
                self._serve_static(path)
            else:
                self.send_error(405, "Method Not Allowed")
            return

        body = {}
        if method in ("POST", "PUT", "PATCH"):
            try:
                body = json_body_or_400(self)
            except ValidationError as e:
                send_error_json(self, 400, str(e))
                return

        for route_method, pattern, func in ROUTES:
            if route_method != method:
                continue
            match = pattern.match(path)
            if match:
                try:
                    func(self, match, query, body)
                except AuthError as e:
                    send_error_json(self, 401, str(e))
                except ValidationError as e:
                    send_error_json(self, 400, str(e))
                except Exception as e:  # pragma: no cover
                    send_error_json(self, 500, f"Internal server error: {e}")
                return

        send_error_json(self, 404, f"No route for {method} {path}")

    def do_GET(self):
        self._dispatch("GET")

    def do_POST(self):
        self._dispatch("POST")

    def do_PUT(self):
        self._dispatch("PUT")

    def do_DELETE(self):
        self._dispatch("DELETE")

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()


def main():
    init_db()
    auth_module.ensure_default_admin()
    try:
        server = ThreadingHTTPServer(("0.0.0.0", PORT), GroceryRequestHandler)
    except OSError as e:
        print(f"\nCould not start server on port {PORT}: {e}")
        print(f"Something else may already be using port {PORT}.")
        print("Close that program, or edit PORT in backend/server.py, then try again.")
        sys.exit(1)
    print("=" * 60)
    print(" Grocery Shop Management System")
    print(f" Server running at: http://localhost:{PORT}/")
    print(" Press Ctrl+C to stop")
    print("=" * 60)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        server.shutdown()


if __name__ == "__main__":
    main()
