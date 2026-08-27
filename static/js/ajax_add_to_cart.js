document.addEventListener('DOMContentLoaded', function(){
  const pendingAdds = [];
  let processing = false;
  let displayedCartCount = Number(document.querySelector('.cart-badge')?.textContent || 0);

  function ensureCartBadge() {
    let badge = document.querySelector('.cart-badge');
    if (!badge) {
      const cartLink = document.querySelector('.header-link[href="/cart/"]');
      if (cartLink) {
        badge = document.createElement('span');
        badge.className = 'cart-badge';
        cartLink.appendChild(badge);
      }
    }
    return badge;
  }

  function ensureCheckoutBar() {
    let fixed = document.querySelector('.fixed-checkout-bar');
    if (!fixed) {
      fixed = document.createElement('div');
      fixed.className = 'fixed-checkout-bar';
      fixed.innerHTML = '<a href="/checkout/" class="btn full clay"></a>';
      document.querySelector('.device')?.appendChild(fixed);
    }
    return fixed.querySelector('a');
  }

  function updateCartUi(cartCount, showToast = false) {
    const badge = cartCount > 0 ? ensureCartBadge() : document.querySelector('.cart-badge');
    if (badge) {
      if (cartCount > 0) badge.textContent = cartCount;
      else badge.remove();
    }

    if (cartCount > 0) {
      const fixed = ensureCheckoutBar();
      if (fixed) fixed.innerHTML = `Go to checkout (${cartCount} item${cartCount!=1 ? 's' : ''})`;
    } else {
      document.querySelector('.fixed-checkout-bar')?.remove();
    }

    if (showToast && window.showToastAdded) window.showToastAdded(cartCount);
  }

  function submitCartAction(e) {
    e.preventDefault();
    const form = e.currentTarget;
    const button = form.querySelector('button[type="submit"]');
    if (button) button.disabled = true;

    fetch(form.action, {
      method: 'POST',
      body: new FormData(form),
      headers: { 'X-Requested-With': 'XMLHttpRequest' },
      credentials: 'same-origin'
    }).then(response => response.json()).then(payload => {
      if (!payload || !payload.success) throw new Error('Cart update failed');
      updateCartUi(payload.cart_count);
      const line = document.querySelector(`.cart-line[data-variant-id="${payload.variant_id}"]`);
      if (payload.quantity > 0 && line) {
        line.querySelector('.qty-input').value = payload.quantity;
        line.querySelector('.line-total').textContent = `₹${payload.line_total}`;
      } else if (line) {
        line.remove();
      }
      const subtotal = document.querySelector('.cart-subtotal');
      if (subtotal) subtotal.textContent = `₹${payload.subtotal}`;
      if (!document.querySelector('.cart-line')) {
        document.querySelector('.cart-content').innerHTML =
          '<div class="empty">Your cart is empty.<br><a href="/" class="btn secondary" style="margin-top:14px;">Browse vegetables</a></div>';
      }
    }).catch(() => {
      form.submit();
    }).finally(() => {
      if (button) button.disabled = false;
    });
  }

  function processNextAdd() {
    if (processing || !pendingAdds.length) return;
    processing = true;
    const form = pendingAdds.shift();
    const button = form.querySelector('button[type="submit"]');
    if (button) button.disabled = true;

    fetch(form.action, {
      method: 'POST',
      body: new FormData(form),
      headers: { 'X-Requested-With': 'XMLHttpRequest' },
      credentials: 'same-origin'
    }).then(response => response.json()).then(payload => {
      if (payload && payload.success) {
        displayedCartCount = Math.max(displayedCartCount, payload.cart_count);
        updateCartUi(displayedCartCount);
        return;
      }
      window.location = form.querySelector('input[name="next"]')?.value || window.location.href;
    }).catch(() => {
      window.location = form.querySelector('input[name="next"]')?.value || window.location.href;
    }).finally(() => {
      if (button) button.disabled = false;
      processing = false;
      processNextAdd();
    });
  }

  function onSubmit(e){
    e.preventDefault();
    const form = e.currentTarget;
    const quantity = Number(form.querySelector('input[name="quantity"]')?.value || 1);
    pendingAdds.push(form);
    displayedCartCount += quantity;
    updateCartUi(displayedCartCount, true);
    processNextAdd();
  }

  document.querySelectorAll('form.ajax-add').forEach(f => {
    f.addEventListener('submit', onSubmit);
  });
  document.querySelectorAll('form.ajax-cart-action').forEach(f => {
    f.addEventListener('submit', submitCartAction);
  });
});
