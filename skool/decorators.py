from functools import wraps

from django.shortcuts import redirect

from .guest_auth import session_user


def skool_user_required(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        request.skool_user = session_user(request)
        if not request.skool_user or not request.skool_user.withdrawal_notice_accepted_at:
            return redirect("skool:onboarding")
        return view(request, *args, **kwargs)
    return wrapped
