document.addEventListener('DOMContentLoaded', function(){
  function onSubmit(e){
    e.preventDefault();
    const form = e.currentTarget;
    const url = form.action;
    const data = new FormData(form);

    fetch(url, {
      method: 'POST',
      body: data,
      headers: { 'X-Requested-With': 'XMLHttpRequest' },
      credentials: 'same-origin'
    }).then(r => r.json()).then(payload => {
      if (payload && payload.success) {
        // update cart badge
        const badge = document.querySelector('.cart-badge');
        if (badge) badge.textContent = payload.cart_count;
        // update fixed checkout bar text
        const fixed = document.querySelector('.fixed-checkout-bar a');
        if (fixed) fixed.innerHTML = `Go to checkout (${payload.cart_count} item${payload.cart_count!=1 ? 's' : ''})`;
        // show toast
        if (window.showToastAdded) window.showToastAdded(payload.cart_count);
        // if there's a next param requesting a redirect, ignore because we're staying on page
      } else {
        // fallback to full page redirect on error
        window.location = form.querySelector('input[name="next"]')?.value || window.location.href;
      }
    }).catch(() => {
      // network error: fall back to normal submit
      form.submit();
    });
  }

  document.querySelectorAll('form.ajax-add').forEach(f => {
    f.addEventListener('submit', onSubmit);
  });
});
