"""Community-only authentication, including session invalidation after password changes."""
from django.utils.crypto import constant_time_compare
from .models import SkoolGuestAccount, SkoolUser

GUEST_KEYS = ("skool_user_id", "skool_guest_pending_id", "skool_guest_auth", "skool_invite_hash")


def clear_guest_session(request):
    for key in GUEST_KEYS:
        request.session.pop(key, None)
    request.session.cycle_key()


def pending_guest(request):
    pk = request.session.get("skool_guest_pending_id")
    if not pk:
        return None
    try:
        account = SkoolGuestAccount.objects.select_related("user__invitation").filter(pk=pk, is_active=True).first()
    except (ValueError, TypeError):
        clear_guest_session(request)
        return None
    if (account and account.must_change_password and account.user.invitation.status == "claimed"
            and constant_time_compare(request.session.get("skool_guest_auth", ""), account.session_hash())):
        return account
    clear_guest_session(request)
    return None


def session_user(request):
    user_id = request.session.get("skool_user_id")
    try:
        user = SkoolUser.objects.select_related("invitation", "guest_account").filter(pk=user_id).first() if user_id else None
    except (ValueError, TypeError):
        clear_guest_session(request)
        return None
    if not user:
        return None
    if user.invitation.status != "claimed":
        clear_guest_session(request)
        return None
    try:
        guest = user.guest_account
    except SkoolGuestAccount.DoesNotExist:
        return user
    if (not guest.is_active or guest.must_change_password or not constant_time_compare(
            request.session.get("skool_guest_auth", ""), guest.session_hash())):
        clear_guest_session(request)
        return None
    return user
