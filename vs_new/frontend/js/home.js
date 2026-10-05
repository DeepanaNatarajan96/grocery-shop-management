/* home.js — populates the homepage: stats, featured products, categories */

function productCardHtml(p) {
  const inStock = p.quantity > (p.low_stock_threshold || 5);
  const stockLabel = p.quantity <= 0 ? "Out of stock" : (inStock ? "In stock" : "Low stock");
  return `
    <div class="product-card">
      <div class="product-thumb">
        <span class="stock-badge ${p.quantity > 0 ? (inStock ? "ok" : "") : ""}">${stockLabel}</span>
        ${escapeHtml(p.image || "🛒")}
      </div>
      <div class="product-body">
        <span class="product-category">${escapeHtml(p.category_name || "Uncategorised")}</span>
        <h3 class="product-name">${escapeHtml(p.name)}</h3>
        <p class="product-desc">${escapeHtml(p.description || "")}</p>
        <div class="product-footer">
          <span class="product-price">${formatMoney(p.price)}</span>
          <div class="qty-add">
            <button type="button" class="add-to-cart" data-id="${p.product_id}" ${p.quantity <= 0 ? "disabled" : ""}>
              ${p.quantity <= 0 ? "Sold out" : "Add +"}
            </button>
          </div>
        </div>
      </div>
    </div>
  `;
}

function attachAddToCartHandlers(container, products) {
  container.querySelectorAll(".add-to-cart").forEach((btn) => {
    btn.addEventListener("click", () => {
      const id = parseInt(btn.dataset.id, 10);
      const product = products.find((p) => p.product_id === id);
      if (!product) return;
      Cart.add(product, 1);
      showToast(`${product.name} added to cart`);
    });
  });
}

async function loadFeatured() {
  const grid = document.getElementById("featured-grid");
  try {
    const products = await Api.get("/products");
    const featured = products.filter((p) => p.quantity > 0).slice(0, 8);
    if (featured.length === 0) {
      grid.innerHTML = `<div class="empty-state"><div class="emoji">🛒</div><p>No products available right now.</p></div>`;
      return;
    }
    grid.innerHTML = featured.map(productCardHtml).join("");
    attachAddToCartHandlers(grid, products);

    document.getElementById("stat-products").textContent = products.length;
  } catch (err) {
    grid.innerHTML = `<div class="empty-state"><div class="emoji">⚠️</div><p>${escapeHtml(err.message)}</p></div>`;
  }
}

async function loadCategories() {
  const wrap = document.getElementById("home-categories");
  try {
    const categories = await Api.get("/categories");
    document.getElementById("stat-categories").textContent = categories.length;
    if (categories.length === 0) {
      wrap.innerHTML = `<p>No categories yet.</p>`;
      return;
    }
    wrap.innerHTML = categories
      .map(
        (c) =>
          `<a class="category-chip" href="products.html?category_id=${c.category_id}">${escapeHtml(c.name)} (${c.product_count})</a>`
      )
      .join("");
  } catch (err) {
    wrap.innerHTML = `<p>${escapeHtml(err.message)}</p>`;
  }
}

document.addEventListener("DOMContentLoaded", () => {
  renderHeader("home");
  renderFooter();
  loadFeatured();
  loadCategories();
});
