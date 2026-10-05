/* admin.js — Admin panel: dashboard, product/category/customer CRUD,
   order history, and sales reporting. All data comes from /api/*. */

let categoriesCache = [];

/* -------------------------------------------------------------- Tabs */
function initTabs() {
  const buttons = document.querySelectorAll(".tab-btn");
  buttons.forEach((btn) => {
    btn.addEventListener("click", () => {
      buttons.forEach((b) => b.classList.remove("active"));
      document.querySelectorAll(".tab-panel").forEach((p) => p.classList.remove("active"));
      btn.classList.add("active");
      document.getElementById(`tab-${btn.dataset.tab}`).classList.add("active");
      if (btn.dataset.tab === "reports") loadReports();
      if (btn.dataset.tab === "orders") loadOrders();
    });
  });
}

/* -------------------------------------------------------------- Modal */
function openAdminModal(title, bodyHtml) {
  document.getElementById("admin-modal-title").textContent = title;
  document.getElementById("admin-modal-body").innerHTML = bodyHtml;
  document.getElementById("admin-modal").classList.add("open");
}
function closeAdminModal() {
  document.getElementById("admin-modal").classList.remove("open");
}
document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("admin-modal-close").addEventListener("click", closeAdminModal);
  document.getElementById("admin-modal").addEventListener("click", (e) => {
    if (e.target.id === "admin-modal") closeAdminModal();
  });
});

/* -------------------------------------------------------------- Dashboard */
async function loadDashboard() {
  const el = document.getElementById("dashboard-stats");
  try {
    const [products, categories, customers, lowStock] = await Promise.all([
      Api.get("/products"),
      Api.get("/categories"),
      Api.get("/customers"),
      Api.get("/products-low-stock"),
    ]);
    el.innerHTML = `
      <div class="stat-card"><b>${products.length}</b><span>Total Products</span></div>
      <div class="stat-card"><b>${categories.length}</b><span>Categories</span></div>
      <div class="stat-card"><b>${customers.length}</b><span>Registered Customers</span></div>
      <div class="stat-card ${lowStock.length > 0 ? "alert" : ""}">
        <b>${lowStock.length}</b><span>Low Stock Alerts</span>
      </div>
    `;
  } catch (err) {
    el.innerHTML = `<p>${escapeHtml(err.message)}</p>`;
  }
}

/* -------------------------------------------------------------- Products */
async function loadProducts() {
  const tbody = document.getElementById("products-table-body");
  try {
    const [products, categories] = await Promise.all([
      Api.get("/products"),
      Api.get("/categories"),
    ]);
    categoriesCache = categories;

    if (products.length === 0) {
      tbody.innerHTML = `<tr><td colspan="7">No products yet. Add your first product.</td></tr>`;
      return;
    }

    tbody.innerHTML = products
      .map((p) => {
        const low = p.quantity <= (p.low_stock_threshold || 5);
        return `
        <tr>
          <td>#${p.product_id}</td>
          <td><b>${escapeHtml(p.name)}</b></td>
          <td>${escapeHtml(p.category_name || "—")}</td>
          <td>${formatMoney(p.price)}</td>
          <td>${p.quantity}</td>
          <td><span class="badge ${low ? "badge-low" : "badge-ok"}">${low ? "Low stock" : "In stock"}</span></td>
          <td>
            <div class="row-actions">
              <button class="btn btn-outline btn-sm" data-edit="${p.product_id}">Edit</button>
              <button class="btn btn-danger btn-sm" data-delete="${p.product_id}">Delete</button>
            </div>
          </td>
        </tr>`;
      })
      .join("");

    tbody.querySelectorAll("[data-edit]").forEach((btn) =>
      btn.addEventListener("click", () => openProductForm(products.find((p) => p.product_id == btn.dataset.edit)))
    );
    tbody.querySelectorAll("[data-delete]").forEach((btn) =>
      btn.addEventListener("click", () => deleteProduct(parseInt(btn.dataset.delete, 10)))
    );
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="7">${escapeHtml(err.message)}</td></tr>`;
  }
}

function categoryOptionsHtml(selectedId) {
  return categoriesCache
    .map(
      (c) =>
        `<option value="${c.category_id}" ${String(c.category_id) === String(selectedId) ? "selected" : ""}>${escapeHtml(c.name)}</option>`
    )
    .join("");
}

function openProductForm(product) {
  const isEdit = !!product;
  const p = product || { name: "", category_id: "", price: "", quantity: "", description: "", image: "", low_stock_threshold: 5 };

  openAdminModal(isEdit ? `Edit Product #${p.product_id}` : "Add Product", `
    <form id="product-form">
      <div class="form-grid">
        <div class="form-field">
          <label>Product Name</label>
          <input type="text" id="pf-name" required value="${escapeHtml(p.name)}" />
        </div>
        <div class="form-field">
          <label>Category</label>
          <select id="pf-category">
            <option value="">Uncategorised</option>
            ${categoryOptionsHtml(p.category_id)}
          </select>
        </div>
        <div class="form-field">
          <label>Price (₹)</label>
          <input type="number" id="pf-price" min="0" step="0.01" required value="${p.price}" />
        </div>
        <div class="form-field">
          <label>Quantity</label>
          <input type="number" id="pf-quantity" min="0" step="1" required value="${p.quantity}" />
        </div>
        <div class="form-field">
          <label>Low Stock Alert Threshold</label>
          <input type="number" id="pf-threshold" min="0" step="1" value="${p.low_stock_threshold || 5}" />
        </div>
        <div class="form-field">
          <label>Emoji / Image Label</label>
          <input type="text" id="pf-image" maxlength="4" value="${escapeHtml(p.image || "🛒")}" placeholder="🛒" />
        </div>
      </div>
      <div class="form-field" style="margin-top:14px;">
        <label>Description</label>
        <textarea id="pf-description" rows="3">${escapeHtml(p.description || "")}</textarea>
      </div>
      <p class="field-error" id="pf-error"></p>
      <div class="form-actions">
        <button type="submit" class="btn btn-primary btn-block">${isEdit ? "Save Changes" : "Add Product"}</button>
      </div>
    </form>
  `);

  document.getElementById("product-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const errorEl = document.getElementById("pf-error");
    const payload = {
      name: document.getElementById("pf-name").value.trim(),
      category_id: document.getElementById("pf-category").value || null,
      price: parseFloat(document.getElementById("pf-price").value),
      quantity: parseInt(document.getElementById("pf-quantity").value, 10),
      low_stock_threshold: parseInt(document.getElementById("pf-threshold").value || 5, 10),
      image: document.getElementById("pf-image").value.trim(),
      description: document.getElementById("pf-description").value.trim(),
    };
    try {
      if (isEdit) {
        await Api.put(`/products/${p.product_id}`, payload);
        showToast("Product updated");
      } else {
        await Api.post("/products", payload);
        showToast("Product added");
      }
      closeAdminModal();
      loadProducts();
      loadDashboard();
    } catch (err) {
      errorEl.textContent = err.message;
    }
  });
}

async function deleteProduct(id) {
  if (!confirm("Delete this product? This cannot be undone.")) return;
  try {
    await Api.del(`/products/${id}`);
    showToast("Product deleted");
    loadProducts();
    loadDashboard();
  } catch (err) {
    showToast(err.message, "error");
  }
}

/* -------------------------------------------------------------- Categories */
async function loadCategories() {
  const tbody = document.getElementById("categories-table-body");
  try {
    const categories = await Api.get("/categories");
    categoriesCache = categories;
    if (categories.length === 0) {
      tbody.innerHTML = `<tr><td colspan="5">No categories yet.</td></tr>`;
      return;
    }
    tbody.innerHTML = categories
      .map(
        (c) => `
      <tr>
        <td>#${c.category_id}</td>
        <td><b>${escapeHtml(c.name)}</b></td>
        <td>${escapeHtml(c.description || "—")}</td>
        <td>${c.product_count}</td>
        <td>
          <div class="row-actions">
            <button class="btn btn-outline btn-sm" data-edit="${c.category_id}">Edit</button>
            <button class="btn btn-danger btn-sm" data-delete="${c.category_id}">Delete</button>
          </div>
        </td>
      </tr>`
      )
      .join("");

    tbody.querySelectorAll("[data-edit]").forEach((btn) =>
      btn.addEventListener("click", () => openCategoryForm(categories.find((c) => c.category_id == btn.dataset.edit)))
    );
    tbody.querySelectorAll("[data-delete]").forEach((btn) =>
      btn.addEventListener("click", () => deleteCategory(parseInt(btn.dataset.delete, 10)))
    );
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="5">${escapeHtml(err.message)}</td></tr>`;
  }
}

function openCategoryForm(category) {
  const isEdit = !!category;
  const c = category || { name: "", description: "" };

  openAdminModal(isEdit ? `Edit Category #${c.category_id}` : "Add Category", `
    <form id="category-form">
      <div class="form-field">
        <label>Category Name</label>
        <input type="text" id="cf-name" required value="${escapeHtml(c.name)}" />
      </div>
      <div class="form-field" style="margin-top:14px;">
        <label>Description</label>
        <textarea id="cf-description" rows="3">${escapeHtml(c.description || "")}</textarea>
      </div>
      <p class="field-error" id="cf-error"></p>
      <div class="form-actions">
        <button type="submit" class="btn btn-primary btn-block">${isEdit ? "Save Changes" : "Add Category"}</button>
      </div>
    </form>
  `);

  document.getElementById("category-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const errorEl = document.getElementById("cf-error");
    const payload = {
      name: document.getElementById("cf-name").value.trim(),
      description: document.getElementById("cf-description").value.trim(),
    };
    try {
      if (isEdit) {
        await Api.put(`/categories/${c.category_id}`, payload);
        showToast("Category updated");
      } else {
        await Api.post("/categories", payload);
        showToast("Category added");
      }
      closeAdminModal();
      loadCategories();
      loadDashboard();
    } catch (err) {
      errorEl.textContent = err.message;
    }
  });
}

async function deleteCategory(id) {
  if (!confirm("Delete this category? Products in it will become uncategorised.")) return;
  try {
    await Api.del(`/categories/${id}`);
    showToast("Category deleted");
    loadCategories();
    loadDashboard();
  } catch (err) {
    showToast(err.message, "error");
  }
}

/* -------------------------------------------------------------- Customers */
async function loadCustomers(search) {
  const tbody = document.getElementById("customers-table-body");
  try {
    const customers = search
      ? await Api.get(`/customers?search=${encodeURIComponent(search)}`)
      : await Api.get("/customers");

    if (customers.length === 0) {
      tbody.innerHTML = `<tr><td colspan="6">No customers found.</td></tr>`;
      return;
    }
    tbody.innerHTML = customers
      .map(
        (c) => `
      <tr>
        <td>#${c.customer_id}</td>
        <td><b>${escapeHtml(c.name)}</b></td>
        <td>${escapeHtml(c.phone)}</td>
        <td>${escapeHtml(c.email || "—")}</td>
        <td>${escapeHtml(c.address || "—")}</td>
        <td>
          <div class="row-actions">
            <button class="btn btn-outline btn-sm" data-edit="${c.customer_id}">Edit</button>
            <button class="btn btn-danger btn-sm" data-delete="${c.customer_id}">Delete</button>
          </div>
        </td>
      </tr>`
      )
      .join("");

    tbody.querySelectorAll("[data-edit]").forEach((btn) =>
      btn.addEventListener("click", () => openCustomerForm(customers.find((c) => c.customer_id == btn.dataset.edit)))
    );
    tbody.querySelectorAll("[data-delete]").forEach((btn) =>
      btn.addEventListener("click", () => deleteCustomer(parseInt(btn.dataset.delete, 10)))
    );
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="6">${escapeHtml(err.message)}</td></tr>`;
  }
}

function openCustomerForm(customer) {
  const isEdit = !!customer;
  const c = customer || { name: "", phone: "", email: "", address: "" };

  openAdminModal(isEdit ? `Edit Customer #${c.customer_id}` : "Add Customer", `
    <form id="customer-form">
      <div class="form-grid">
        <div class="form-field">
          <label>Full Name</label>
          <input type="text" id="cuf-name" required value="${escapeHtml(c.name)}" />
        </div>
        <div class="form-field">
          <label>Phone Number</label>
          <input type="text" id="cuf-phone" required value="${escapeHtml(c.phone)}" />
        </div>
        <div class="form-field">
          <label>Email</label>
          <input type="email" id="cuf-email" value="${escapeHtml(c.email || "")}" />
        </div>
        <div class="form-field">
          <label>Address</label>
          <input type="text" id="cuf-address" value="${escapeHtml(c.address || "")}" />
        </div>
      </div>
      <p class="field-error" id="cuf-error"></p>
      <div class="form-actions">
        <button type="submit" class="btn btn-primary btn-block">${isEdit ? "Save Changes" : "Add Customer"}</button>
      </div>
    </form>
  `);

  document.getElementById("customer-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const errorEl = document.getElementById("cuf-error");
    const payload = {
      name: document.getElementById("cuf-name").value.trim(),
      phone: document.getElementById("cuf-phone").value.trim(),
      email: document.getElementById("cuf-email").value.trim(),
      address: document.getElementById("cuf-address").value.trim(),
    };
    try {
      if (isEdit) {
        await Api.put(`/customers/${c.customer_id}`, payload);
        showToast("Customer updated");
      } else {
        await Api.post("/customers", payload);
        showToast("Customer added");
      }
      closeAdminModal();
      loadCustomers();
      loadDashboard();
    } catch (err) {
      errorEl.textContent = err.message;
    }
  });
}

async function deleteCustomer(id) {
  if (!confirm("Delete this customer record?")) return;
  try {
    await Api.del(`/customers/${id}`);
    showToast("Customer deleted");
    loadCustomers();
    loadDashboard();
  } catch (err) {
    showToast(err.message, "error");
  }
}

/* -------------------------------------------------------------- Orders */
async function loadOrders() {
  const tbody = document.getElementById("orders-table-body");
  tbody.innerHTML = `<tr><td colspan="6">Loading…</td></tr>`;
  try {
    const orders = await Api.get("/orders");
    if (orders.length === 0) {
      tbody.innerHTML = `<tr><td colspan="6">No orders placed yet.</td></tr>`;
      return;
    }
    tbody.innerHTML = orders
      .map(
        (o) => `
      <tr>
        <td>#${o.order_id}</td>
        <td>${escapeHtml(o.order_date)}</td>
        <td>${escapeHtml(o.customer_name || "Walk-in customer")}</td>
        <td>${formatMoney(o.total_amount)}</td>
        <td><span class="badge badge-ok">${escapeHtml(o.status)}</span></td>
        <td><button class="btn btn-outline btn-sm" data-view="${o.order_id}">View Bill</button></td>
      </tr>`
      )
      .join("");

    tbody.querySelectorAll("[data-view]").forEach((btn) =>
      btn.addEventListener("click", () => viewOrderBill(parseInt(btn.dataset.view, 10)))
    );
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="6">${escapeHtml(err.message)}</td></tr>`;
  }
}

async function viewOrderBill(orderId) {
  try {
    const detail = await Api.get(`/orders/${orderId}`);
    const bill = detail.bill;
    const itemsHtml = detail.items
      .map((i) => `<div class="receipt-line"><span>${escapeHtml(i.product_name)} × ${i.quantity}</span><span>${formatMoney(i.subtotal)}</span></div>`)
      .join("");
    openAdminModal(`Bill for Order #${orderId}`, `
      <div class="receipt" style="border:none; padding:0;">
        ${itemsHtml}
        <hr/>
        <div class="receipt-line"><span>Subtotal</span><span>${formatMoney(bill.subtotal)}</span></div>
        <div class="receipt-line"><span>Tax</span><span>${formatMoney(bill.tax)}</span></div>
        <div class="receipt-line"><span>Discount</span><span>-${formatMoney(bill.discount)}</span></div>
        <div class="receipt-line" style="font-weight:700;"><span>Total</span><span>${formatMoney(bill.total_amount)}</span></div>
      </div>
    `);
  } catch (err) {
    showToast(err.message, "error");
  }
}

/* -------------------------------------------------------------- Reports */
async function loadReports() {
  const statsEl = document.getElementById("report-stats");
  const topBody = document.getElementById("top-products-body");
  const dailyBody = document.getElementById("daily-sales-body");
  try {
    const report = await Api.get("/reports/sales");
    statsEl.innerHTML = `
      <div class="stat-card"><b>${report.total_orders}</b><span>Total Orders</span></div>
      <div class="stat-card"><b>${formatMoney(report.total_revenue)}</b><span>Total Revenue</span></div>
      <div class="stat-card"><b>${report.orders_today}</b><span>Orders Today</span></div>
      <div class="stat-card"><b>${formatMoney(report.revenue_today)}</b><span>Revenue Today</span></div>
    `;
    topBody.innerHTML = report.top_products.length
      ? report.top_products.map((p) => `<tr><td>${escapeHtml(p.product_name)}</td><td>${p.units_sold}</td><td>${formatMoney(p.revenue)}</td></tr>`).join("")
      : `<tr><td colspan="3">No sales yet.</td></tr>`;
    dailyBody.innerHTML = report.daily_sales.length
      ? report.daily_sales.map((d) => `<tr><td>${escapeHtml(d.day)}</td><td>${d.orders}</td><td>${formatMoney(d.revenue)}</td></tr>`).join("")
      : `<tr><td colspan="3">No sales yet.</td></tr>`;
  } catch (err) {
    statsEl.innerHTML = `<p>${escapeHtml(err.message)}</p>`;
  }
}

/* -------------------------------------------------------------- Account */
function openChangePasswordForm() {
  openAdminModal("Change Password", `
    <form id="password-form">
      <div class="form-field">
        <label>Current Password</label>
        <input type="password" id="pw-old" required />
      </div>
      <div class="form-field" style="margin-top:14px;">
        <label>New Password</label>
        <input type="password" id="pw-new" required minlength="4" />
      </div>
      <p class="field-error" id="pw-error"></p>
      <div class="form-actions">
        <button type="submit" class="btn btn-primary btn-block">Update Password</button>
      </div>
    </form>
  `);

  document.getElementById("password-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const errorEl = document.getElementById("pw-error");
    try {
      await Api.post("/change-password", {
        old_password: document.getElementById("pw-old").value,
        new_password: document.getElementById("pw-new").value,
      });
      showToast("Password updated. Please log in again.");
      Auth.clear();
      window.location.href = "login.html";
    } catch (err) {
      errorEl.textContent = err.message;
    }
  });
}

/* -------------------------------------------------------------- Init */
function init() {
  if (!Auth.isLoggedIn()) {
    window.location.href = "login.html";
    return;
  }

  renderHeader("admin");
  renderFooter();
  initTabs();
  loadDashboard();
  loadProducts();
  loadCategories();
  loadCustomers();

  document.getElementById("add-product-btn").addEventListener("click", () => openProductForm(null));
  document.getElementById("add-category-btn").addEventListener("click", () => openCategoryForm(null));
  document.getElementById("add-customer-btn").addEventListener("click", () => openCustomerForm(null));
  document.getElementById("change-password-btn").addEventListener("click", openChangePasswordForm);

  let searchTimer;
  document.getElementById("customer-search-input").addEventListener("input", (e) => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => loadCustomers(e.target.value.trim()), 250);
  });
}

document.addEventListener("DOMContentLoaded", init);
