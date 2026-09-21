PRIVACY_VERSION = '2026-09-20'


def accepted(user):
    return bool(user.privacy_accepted_at and user.privacy_version == PRIVACY_VERSION)


class PrivacyMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        from django.shortcuts import redirect
        from django.urls import resolve, Resolver404
        if request.user.is_authenticated and not accepted(request.user):
            try:
                match = resolve(request.path_info)
            except Resolver404:
                return self.get_response(request)
            if match.url_name not in {'card_entry', 'card_workspace', 'card_save', 'card_leave', 'privacy', 'signin', 'root', 'signout', 'logout', 'change_password', 'organization_logo'}:
                return redirect('privacy')
        return self.get_response(request)
