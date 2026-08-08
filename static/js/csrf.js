(function(){
  function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
      const cookies = document.cookie.split(';');
      for (let i = 0; i < cookies.length; i++) {
        const cookie = cookies[i].trim();
        if (cookie.startsWith(name + '=')) {
          cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
          break;
        }
      }
    }
    return cookieValue;
  }

  const csrftoken = getCookie('csrftoken');

  // Attach X-CSRFToken header to fetch calls when not already present
  const nativeFetch = window.fetch.bind(window);
  window.fetch = function(input, init){
    init = init || {};
    init.headers = init.headers || {};
    // Only add token for state-changing requests
    const method = (init.method || 'GET').toUpperCase();
    if (['POST','PUT','PATCH','DELETE'].includes(method) && csrftoken) {
      if (init.headers instanceof Headers) {
        if (!init.headers.has('X-CSRFToken')) init.headers.set('X-CSRFToken', csrftoken);
      } else if (typeof init.headers === 'object') {
        if (!('X-CSRFToken' in init.headers)) init.headers['X-CSRFToken'] = csrftoken;
      }
    }
    return nativeFetch(input, init);
  };
})();
