/* =========================================================================
   main.js
   Shared utilities used across every page: API client, cart (localStorage),
   toast notifications, and header/footer partial rendering.
   ========================================================================= */

/* -------------------------------------------------------- File:// guard --
   If someone double-clicks index.html instead of running the Python
   server, fetch() calls to /api/* silently fail under the file:// origin.
   Show a clear, unmissable banner instead of a blank/broken page.
---------------------------------------------------------------------------*/
function checkServerReachable() {
  if (window.location.protocol === "file:") {
    showServerWarningBanner(
      "This page was opened directly as a file. Start the Python server first (see README), then open http://localhost:8000/ in your browser."
    );
    return;
  }
  fetch(API_BASE + "/categories").catch(() => {
    showServerWarningBanner(
      "Can't reach the backend server. Make sure it's running: open a terminal in the backend/ folder and run: python server.py (or python3 server.py)"
    );
  });
}

function showServerWarningBanner(message) {
  if (document.getElementById("server-warning-banner")) return;
  const banner = document.createElement("div");
  banner.id = "server-warning-banner";
  banner.style.cssText =
    "position:sticky;top:0;z-index:1000;background:#C24534;color:#fff;padding:12px 20px;" +
    "text-align:center;font-family:'Work Sans',sans-serif;font-size:0.9rem;font-weight:600;";
  banner.textContent = "⚠️ " + message;
  document.body.prepend(banner);
}

/* -------------------------------------------------------------- API client */
const API_BASE = "/api";

/* -------------------------------------------------------------- Auth ----
   Session token issued by POST /api/login, kept in localStorage and sent
   back as "Authorization: Bearer <token>" on every admin API call.
---------------------------------------------------------------------------*/
const AUTH_KEY = "grocery_admin_auth_v1";

const Auth = {
  getSession() {
    try {
      return JSON.parse(localStorage.getItem(AUTH_KEY));
    } catch (e) {
      return null;
    }
  },
  getToken() {
    const s = this.getSession();
    return s ? s.token : null;
  },
  getUser() {
    const s = this.getSession();
    return s ? s.user : null;
  },
  setSession(token, user) {
    localStorage.setItem(AUTH_KEY, JSON.stringify({ token, user }));
  },
  clear() {
    localStorage.removeItem(AUTH_KEY);
  },
  isLoggedIn() {
    return !!this.getToken();
  },
};

/* ------------------------------------------------------------ API client */
const Api = {
  async request(method, path, body) {
    const opts = { method, headers: {} };
    const token = Auth.getToken();
    if (token) opts.headers["Authorization"] = "Bearer " + token;
    if (body !== undefined) {
      opts.headers["Content-Type"] = "application/json";
      opts.body = JSON.stringify(body);
    }
    let res;
    try {
      res = await fetch(API_BASE + path, opts);
    } catch (networkErr) {
      throw new Error(
        "Can't reach the backend server. Make sure it's running (python server.py in the backend/ folder) and that you're viewing this page at http://localhost:8000/."
      );
    }
    let json;
    let rawText = "";
    try {
      rawText = await res.text();
      json = JSON.parse(rawText);
    } catch (e) {
      const preview = rawText ? rawText.slice(0, 160).replace(/\s+/g, " ").trim() : "(empty response body)";
      throw new Error(
        `Server returned an invalid response (HTTP ${res.status}). This usually means another program is using port 8000, or a browser extension/antivirus is blocking the request. Raw response: "${preview}"`
      );
    }
    if (res.status === 401) {
      Auth.clear();
      if (!window.location.pathname.endsWith("login.html")) {
        window.location.href = "login.html";
      }
      throw new Error(json.error || "Please log in again.");
    }
    if (!res.ok || json.success === false) {
      throw new Error(json.error || `Request failed (${res.status})`);
    }
    return json.data;
  },
  get(path) { return this.request("GET", path); },
  post(path, body) { return this.request("POST", path, body); },
  put(path, body) { return this.request("PUT", path, body); },
  del(path) { return this.request("DELETE", path); },
};

/* -------------------------------------------------------------- Toasts */
function showToast(message, type = "success") {
  let stack = document.getElementById("toast-stack");
  if (!stack) {
    stack = document.createElement("div");
    stack.id = "toast-stack";
    document.body.appendChild(stack);
  }
  const toast = document.createElement("div");
  toast.className = "toast" + (type === "error" ? " error" : "");
  toast.textContent = message;
  stack.appendChild(toast);
  setTimeout(() => toast.remove(), 3200);
}

function formatMoney(n) {
  const num = Number(n) || 0;
  return "₹" + num.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function escapeHtml(str) {
  if (str === null || str === undefined) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

/* -------------------------------------------------------------- Cart -----
   Cart is kept in localStorage as: [{product_id, name, price, image, qty}]
   This is browser-side scratch state; the authoritative stock/price data
   always lives in SQLite and is re-validated at checkout time by the
   server (see backend/orders.py -> checkout()).
---------------------------------------------------------------------------*/
const CART_KEY = "grocery_cart_v1";

const Cart = {
  getItems() {
    try {
      return JSON.parse(localStorage.getItem(CART_KEY)) || [];
    } catch (e) {
      return [];
    }
  },
  save(items) {
    localStorage.setItem(CART_KEY, JSON.stringify(items));
    updateCartBadge();
  },
  add(product, qty = 1) {
    const items = this.getItems();
    const existing = items.find((i) => i.product_id === product.product_id);
    if (existing) {
      existing.qty += qty;
    } else {
      items.push({
        product_id: product.product_id,
        name: product.name,
        price: product.price,
        image: product.image || "🛒",
        qty: qty,
      });
    }
    this.save(items);
  },
  updateQty(productId, qty) {
    let items = this.getItems();
    if (qty <= 0) {
      items = items.filter((i) => i.product_id !== productId);
    } else {
      const item = items.find((i) => i.product_id === productId);
      if (item) item.qty = qty;
    }
    this.save(items);
  },
  remove(productId) {
    const items = this.getItems().filter((i) => i.product_id !== productId);
    this.save(items);
  },
  clear() {
    this.save([]);
  },
  count() {
    return this.getItems().reduce((sum, i) => sum + i.qty, 0);
  },
  subtotal() {
    return this.getItems().reduce((sum, i) => sum + i.qty * i.price, 0);
  },
};

function updateCartBadge() {
  const el = document.getElementById("cart-count");
  if (el) el.textContent = Cart.count();
}

/* -------------------------------------------------------- Header/Footer */
const ICON = {
  menu: '<svg viewBox="0 0 24 24"><path d="M3 6h18M3 12h18M3 18h18"/></svg>',
  user: '<svg viewBox="0 0 24 24"><circle cx="12" cy="8" r="4"/><path d="M4 21c1-4 4-6 8-6s7 2 8 6"/></svg>',
  cart: '<svg viewBox="0 0 24 24"><path d="M2 3h3l2.5 12h11L21 7H6"/><circle cx="9" cy="20" r="1.4"/><circle cx="18" cy="20" r="1.4"/></svg>',
  home: '<svg viewBox="0 0 24 24"><path d="M3 10l2-6h14l2 6M4 10v10h16V10M9 20v-6h6v6"/></svg>',
  products: '<svg viewBox="0 0 24 24"><path d="M5 3h14v18l-3-2-2 2-2-2-2 2-2-2-3 2z"/><path d="M9 8h6M9 12h6"/></svg>',
  categories: '<svg viewBox="0 0 24 24"><circle cx="7" cy="7" r="3"/><circle cx="17" cy="7" r="3"/><circle cx="7" cy="17" r="3"/><circle cx="17" cy="17" r="3"/></svg>',
};

function renderHeader(activePage) {
  const mount = document.getElementById("site-header");
  if (!mount) return;
  const user = Auth.getUser();
  const links = [["index.html","Welcome"],["products.html","Products"],["categories.html","Categories"],["cart.html","My Cart"],["contact.html","Contact"],
    Auth.isLoggedIn() ? ["admin.html","Admin Panel"] : ["login.html","Admin Login"]]
    .map(([h,l]) => `<a href="${h}">${l}</a>`).join("") +
    (Auth.isLoggedIn() ? `<a href="#" id="header-logout-btn">Logout</a>` : "");
  mount.innerHTML = `
    <div class="topbar">
      <button type="button" id="menu-btn" aria-label="Menu">${ICON.menu}</button>
      <span class="hello">Hello, ${escapeHtml(user?.username || "Guest")}</span>
      <a href="${Auth.isLoggedIn() ? "admin.html" : "login.html"}" aria-label="Account">${ICON.user}</a>
    </div>
    <nav class="menu-drawer" id="menu-drawer">${links}</nav>
    <div class="sheet">
      <form class="search-form" id="global-search-form" role="search">
        <button type="submit" aria-label="Search">🔍</button>
        <input type="text" id="global-search-input" placeholder="Search here…" autocomplete="off" />
      </form>
    </div>`;
  document.getElementById("menu-btn").addEventListener("click", () =>
    document.getElementById("menu-drawer").classList.toggle("open"));
  const logoutBtn = document.getElementById("header-logout-btn");
  if (logoutBtn) logoutBtn.addEventListener("click", async (e) => {
    e.preventDefault();
    try { await Api.post("/logout"); } catch (err) {}
    Auth.clear(); window.location.href = "login.html";
  });
  const form = document.getElementById("global-search-form");
  if (!window.location.pathname.endsWith("products.html")) {
    form.addEventListener("submit", (e) => {
      e.preventDefault();
      const q = document.getElementById("global-search-input").value.trim();
      window.location.href = "products.html" + (q ? `?search=${encodeURIComponent(q)}` : "");
    });
  }
  window.__activePage = activePage;
}

function renderFooter() {
  const mount = document.getElementById("site-footer");
  if (!mount) return;
  const act = window.__activePage || "";
  const item = (href, key, icon, extra = "") =>
    `<a href="${href}" class="${act === key ? "active" : ""}" aria-label="${key}">${icon}${extra}</a>`;
  mount.innerHTML = `<nav class="bnav">
    ${item("cart.html","cart",ICON.cart,'<span class="count" id="cart-count">0</span>')}
    ${item("index.html","home",ICON.home)}
    ${item("products.html","products",ICON.products)}
    ${item("categories.html","categories",ICON.categories)}
    ${item("contact.html","contact",ICON.user)}
  </nav>`;
  updateCartBadge();
}

function getQueryParam(name) {
  return new URLSearchParams(window.location.search).get(name);
}

document.addEventListener("DOMContentLoaded", () => {
  updateCartBadge();
  checkServerReachable();
});
