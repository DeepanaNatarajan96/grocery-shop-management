/* cart.js — cart rendering, quantity controls, checkout, and receipt */

const TAX_RATE = 0.05;
const DISCOUNT_THRESHOLD = 1000;
const FLAT_DISCOUNT = 50;

function computeTotals() {
  const subtotal = Cart.subtotal();
  const tax = subtotal * TAX_RATE;
  const discount = subtotal >= DISCOUNT_THRESHOLD ? FLAT_DISCOUNT : 0;
  const total = subtotal + tax - discount;
  return { subtotal, tax, discount, total };
}

function renderCart() {
  const listEl = document.getElementById("cart-items-list");
  const items = Cart.getItems();

  if (items.length === 0) {
    listEl.innerHTML = `
      <div class="empty-state">
        <div class="emoji">🧺</div>
        <p>Your cart is empty.</p>
        <a href="products.html" class="btn btn-gold">Browse Products</a>
      </div>`;
  } else {
    listEl.innerHTML = items
      .map(
        (item) => `
      <div class="cart-item" data-id="${item.product_id}">
        <div class="thumb">${escapeHtml(item.image || "🛒")}</div>
        <div class="info">
          <b>${escapeHtml(item.name)}</b>
          <span>${formatMoney(item.price)} each</span>
        </div>
        <div class="qty-controls">
          <button type="button" class="qty-minus" aria-label="Decrease quantity">−</button>
          <span>${item.qty}</span>
          <button type="button" class="qty-plus" aria-label="Increase quantity">+</button>
        </div>
        <div style="text-align:right;">
          <div style="font-weight:600;">${formatMoney(item.price * item.qty)}</div>
          <button type="button" class="remove-btn">Remove</button>
        </div>
      </div>`
      )
      .join("");

    listEl.querySelectorAll(".cart-item").forEach((row) => {
      const id = parseInt(row.dataset.id, 10);
      const item = items.find((i) => i.product_id === id);
      row.querySelector(".qty-plus").addEventListener("click", () => {
        Cart.updateQty(id, item.qty + 1);
        renderCart();
      });
      row.querySelector(".qty-minus").addEventListener("click", () => {
        Cart.updateQty(id, item.qty - 1);
        renderCart();
      });
      row.querySelector(".remove-btn").addEventListener("click", () => {
        Cart.remove(id);
        renderCart();
        showToast(`${item.name} removed from cart`);
      });
    });
  }

  const totals = computeTotals();
  document.getElementById("sum-subtotal").textContent = formatMoney(totals.subtotal);
  document.getElementById("sum-tax").textContent = formatMoney(totals.tax);
  document.getElementById("sum-discount").textContent = "-" + formatMoney(totals.discount);
  document.getElementById("sum-total").textContent = formatMoney(totals.total);

  document.getElementById("checkout-btn").disabled = items.length === 0;
}

function openModal(id) { document.getElementById(id).classList.add("open"); }
function closeModal(id) { document.getElementById(id).classList.remove("open"); }

async function handleCheckoutSubmit(e) {
  e.preventDefault();
  const errorEl = document.getElementById("checkout-error");
  errorEl.textContent = "";

  const items = Cart.getItems();
  if (items.length === 0) {
    errorEl.textContent = "Your cart is empty.";
    return;
  }

  const payload = {
    items: items.map((i) => ({ product_id: i.product_id, quantity: i.qty })),
    customer: {
      name: document.getElementById("cust-name").value.trim(),
      phone: document.getElementById("cust-phone").value.trim(),
      email: document.getElementById("cust-email").value.trim(),
      address: document.getElementById("cust-address").value.trim(),
    },
  };

  const btn = document.getElementById("place-order-btn");
  btn.disabled = true;
  btn.textContent = "Placing order…";

  try {
    const bill = await Api.post("/checkout", payload);
    Cart.clear();
    renderCart();
    closeModal("checkout-modal");
    renderBill(bill);
    openModal("bill-modal");
  } catch (err) {
    errorEl.textContent = err.message;
  } finally {
    btn.disabled = false;
    btn.textContent = "Place Order";
  }
}

function renderBill(bill) {
  const content = document.getElementById("bill-content");
  const itemsHtml = bill.items
    .map(
      (i) => `
      <div class="receipt-line">
        <span>${escapeHtml(i.product_name)} × ${i.quantity}</span>
        <span>${formatMoney(i.subtotal)}</span>
      </div>`
    )
    .join("");

  content.innerHTML = `
    <div class="receipt">
      <h3>GreenBasket</h3>
      <p class="sub">Bill #${bill.bill_id} · Order #${bill.order_id}<br/>${escapeHtml(bill.bill_date)}</p>
      ${bill.customer ? `<p class="sub"><strong>${escapeHtml(bill.customer.name)}</strong> · ${escapeHtml(bill.customer.phone)}</p>` : ""}
      <hr/>
      ${itemsHtml}
      <hr/>
      <div class="receipt-line"><span>Subtotal</span><span>${formatMoney(bill.subtotal)}</span></div>
      <div class="receipt-line"><span>Tax (5%)</span><span>${formatMoney(bill.tax)}</span></div>
      <div class="receipt-line"><span>Discount</span><span>-${formatMoney(bill.discount)}</span></div>
      <hr/>
      <div class="receipt-line" style="font-weight:700; font-size:1.05rem;">
        <span>Total Paid</span><span>${formatMoney(bill.total_amount)}</span>
      </div>
    </div>
  `;
}

function init() {
  renderHeader("cart");
  renderFooter();
  renderCart();

  document.getElementById("clear-cart-btn").addEventListener("click", () => {
    if (Cart.getItems().length === 0) return;
    Cart.clear();
    renderCart();
    showToast("Cart cleared");
  });

  document.getElementById("checkout-btn").addEventListener("click", () => {
    if (Cart.getItems().length === 0) return;
    openModal("checkout-modal");
  });
  document.getElementById("close-checkout-modal").addEventListener("click", () => closeModal("checkout-modal"));
  document.getElementById("checkout-form").addEventListener("submit", handleCheckoutSubmit);

  document.getElementById("close-bill-modal").addEventListener("click", () => closeModal("bill-modal"));
  document.getElementById("continue-shopping-btn").addEventListener("click", () => {
    closeModal("bill-modal");
    window.location.href = "products.html";
  });
}

document.addEventListener("DOMContentLoaded", init);
