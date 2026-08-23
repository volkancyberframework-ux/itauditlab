from functools import wraps

from django.shortcuts import redirect

from .models import SkoolUser


def skool_user_required(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        user_id = request.session.get("skool_user_id")
        try:
            request.skool_user = SkoolUser.objects.select_related("invitation").get(pk=user_id)
            if request.skool_user.invitation.status == "revoked":
                request.session.flush()
                return redirect("skool:onboarding")
        except (SkoolUser.DoesNotExist, TypeError, ValueError):
            return redirect("skool:onboarding")
        return view(request, *args, **kwargs)
    return wrapped
