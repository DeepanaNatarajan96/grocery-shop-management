/* products.js — product listing with category filter, search, sort */

let allProducts = [];
let allCategories = [];
let activeCategoryId = null;

function productCardHtml(p) {
  const inStock = p.quantity > (p.low_stock_threshold || 5);
  const stockLabel = p.quantity <= 0 ? "Out of stock" : (inStock ? "In stock" : `${p.quantity} left`);
  return `
    <div class="product-card">
      <div class="product-thumb">${escapeHtml(p.image || "🛒")}</div>
      <div class="product-body">
        <h3 class="product-name">${escapeHtml(p.name)}</h3>
        <p class="product-desc">${escapeHtml(p.description || "")}</p>
        <div class="product-footer">
          <span class="product-unit">${stockLabel}</span>
          <span class="product-price">${formatMoney(p.price)}</span>
        </div>
        <button type="button" class="add-to-cart" data-id="${p.product_id}" ${p.quantity <= 0 ? "disabled" : ""}>
          ${p.quantity <= 0 ? "Sold out" : "Add to Cart"}
        </button>
      </div>
    </div>`;
}

function renderCategoryChips() {
  const wrap = document.getElementById("filter-categories");
  const chips = [`<button type="button" class="category-chip ${!activeCategoryId ? "active" : ""}" data-cat="">All Products</button>`]
    .concat(
      allCategories.map(
        (c) =>
          `<button type="button" class="category-chip ${String(activeCategoryId) === String(c.category_id) ? "active" : ""}" data-cat="${c.category_id}">${escapeHtml(c.name)}</button>`
      )
    );
  wrap.innerHTML = chips.join("");
  wrap.querySelectorAll(".category-chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      activeCategoryId = chip.dataset.cat || null;
      applyFiltersAndRender();
      renderCategoryChips();
    });
  });
}

function applyFiltersAndRender() {
  const grid = document.getElementById("products-grid");
  const search = (document.getElementById("global-search-input")?.value || getQueryParam("search") || "").toLowerCase();
  const sort = document.getElementById("sort-select").value;

  let list = allProducts.slice();
  if (activeCategoryId) {
    list = list.filter((p) => String(p.category_id) === String(activeCategoryId));
  }
  if (search) {
    list = list.filter(
      (p) =>
        p.name.toLowerCase().includes(search) ||
        (p.description || "").toLowerCase().includes(search)
    );
  }

  switch (sort) {
    case "price-asc": list.sort((a, b) => a.price - b.price); break;
    case "price-desc": list.sort((a, b) => b.price - a.price); break;
    case "stock": list.sort((a, b) => b.quantity - a.quantity); break;
    default: list.sort((a, b) => a.name.localeCompare(b.name));
  }

  document.getElementById("results-count").textContent =
    `${list.length} product${list.length === 1 ? "" : "s"} found`;

  if (list.length === 0) {
    grid.innerHTML = `<div class="empty-state"><div class="emoji">🔍</div><p>No products match your search.</p></div>`;
    return;
  }

  grid.innerHTML = list.map(productCardHtml).join("");
  grid.querySelectorAll(".add-to-cart").forEach((btn) => {
    btn.addEventListener("click", () => {
      const id = parseInt(btn.dataset.id, 10);
      const product = allProducts.find((p) => p.product_id === id);
      if (!product) return;
      Cart.add(product, 1);
      showToast(`${product.name} added to cart`);
    });
  });
}

async function init() {
  renderHeader("products");
  renderFooter();

  const grid = document.getElementById("products-grid");
  activeCategoryId = getQueryParam("category_id");
  const initialSearch = getQueryParam("search");
  if (initialSearch) {
    document.getElementById("global-search-input").value = initialSearch;
  }

  try {
    [allProducts, allCategories] = await Promise.all([
      Api.get("/products"),
      Api.get("/categories"),
    ]);
    renderCategoryChips();
    applyFiltersAndRender();
  } catch (err) {
    grid.innerHTML = `<div class="empty-state"><div class="emoji">⚠️</div><p>${escapeHtml(err.message)}</p></div>`;
  }

  document.getElementById("sort-select").addEventListener("change", applyFiltersAndRender);
  document.getElementById("global-search-form").addEventListener("submit", (e) => {
    e.preventDefault();
    applyFiltersAndRender();
  });
  document.getElementById("global-search-input").addEventListener("input", () => {
    applyFiltersAndRender();
  });
}

document.addEventListener("DOMContentLoaded", init);
