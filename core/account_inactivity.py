"""Retired inactivity policy. Compatibility entry points intentionally do nothing."""

def inactivity_message(user):
    return None


def touch_access(user, *, now=None, force=False):
    return False


def run_due_check(*, now=None):
    return None
