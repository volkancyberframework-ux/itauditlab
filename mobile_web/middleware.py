class AppHostMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        from mobile_api.personal_address import personal_host
        host = request.get_host().split(':')[0].lower()
        if host == 'app.grcustasi.com' or personal_host(host):
            request.urlconf = 'mobile_web.urls'
        return self.get_response(request)
