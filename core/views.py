import logging
from django.http import HttpResponseForbidden
from django.template import loader

logger = logging.getLogger(__name__)

def csrf_failure(request, reason=""):
    """Log CSRF failures for easier debugging in dev environments.

    Django will call this view when CSRF verification fails if
    `CSRF_FAILURE_VIEW` is set to this path.
    """
    meta = {
        'path': request.path,
        'remote_addr': request.META.get('REMOTE_ADDR'),
        'host': request.META.get('HTTP_HOST'),
        'referer': request.META.get('HTTP_REFERER'),
        'user_agent': request.META.get('HTTP_USER_AGENT'),
    }
    logger.warning('CSRF verification failed: %s; request meta: %s', reason, meta)
    try:
        tmpl = loader.get_template('403_csrf.html')
        return HttpResponseForbidden(tmpl.render({}, request))
    except Exception:
        return HttpResponseForbidden('CSRF verification failed. Request has been logged.')
