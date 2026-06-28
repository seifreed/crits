class AjaxCompatMiddleware(object):
    """Restore ``request.is_ajax()``.

    Django dropped ``HttpRequest.is_ajax()`` in 4.0; CRITs relies on it in many
    views. Re-expose it as the historical ``X-Requested-With`` header check so
    those call sites keep working without per-site changes.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.is_ajax = lambda: (
            request.headers.get('x-requested-with') == 'XMLHttpRequest'
        )
        return self.get_response(request)
