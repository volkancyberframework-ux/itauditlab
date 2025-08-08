# core/validators.py
# Minimal shim so historical migrations keep working.
# Do NOT add heavy imports here.

def validate_youtube_url(value):
    # No-op: accept anything. Old migration just needs this symbol to exist.
    return None
