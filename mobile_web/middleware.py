class AppHostMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.get_host().split(':')[0].lower() == 'app.grcustasi.com':
            request.urlconf = 'mobile_web.urls'
        return self.get_response(request)
