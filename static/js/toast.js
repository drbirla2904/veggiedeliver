(function(){
  function createToastElement(message, kind='default', actionsHtml=''){
    const toast = document.createElement('div');
    toast.className = `toast ${kind}`;
    const body = document.createElement('div');
    body.className = 'toast-body';
    body.textContent = message;
    const actions = document.createElement('div');
    actions.className = 'toast-actions';
    actions.innerHTML = actionsHtml;
    toast.append(body, actions);
    return toast;
  }

  function showToastElement(toast, timeout=6000){
    document.body.appendChild(toast);
    setTimeout(()=>toast.classList.add('visible'), 50);
    setTimeout(()=>{ toast.classList.remove('visible'); setTimeout(()=>toast.remove(),300); }, timeout);
  }

  window.showToastAdded = function(cart_count){
    const actions = `<a href="/cart/" class="btn secondary" style="padding:6px 10px; font-size:13px;">View cart</a>` +
                    `<a href="/checkout/" class="btn clay" style="padding:6px 10px; font-size:13px; margin-left:8px;">Checkout</a>`;
    const toast = createToastElement('Added to cart.', 'added', actions);
    showToastElement(toast, 6000);
    // update any visible cart badges
    const badge = document.querySelector('.cart-badge');
    if (badge) badge.textContent = cart_count;
    const fixed = document.querySelector('.fixed-checkout-bar a');
    if (fixed) fixed.innerHTML = `Go to checkout (${cart_count} item${cart_count!=1 ? 's' : ''})`;
  };

  window.showToastGift = function(message){
    const actions = `<a href="/orders/" class="btn secondary" style="padding:6px 10px; font-size:13px;">View orders</a>`;
    const toast = createToastElement(message, 'gift', actions);
    showToastElement(toast, 7000);
  };

  document.addEventListener('DOMContentLoaded', function() {
    const flashes = Array.from(document.querySelectorAll('.flash'));
    flashes.forEach(node => {
      const text = node.textContent.trim();
      const kind = node.classList.contains('error') ? 'error' :
        node.classList.contains('gift') ? 'gift' :
        node.classList.contains('success') ? 'success' : 'default';
      if (text.includes('Added to cart')) {
        // try to read cart badge if server set it in the template
        const badge = document.querySelector('.cart-badge');
        const cart_count = badge ? badge.textContent : '';
        node.remove();
        window.showToastAdded(cart_count || '');
      } else if (node.classList.contains('gift')) {
        const msg = node.textContent.trim();
        node.remove();
        window.showToastGift(msg);
      } else {
        node.remove();
        showToastElement(createToastElement(text, kind), kind === 'error' ? 7000 : 5000);
      }
    });
  });
})();
