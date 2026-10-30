"""Small child of the existing web master; runs the daily database check once."""
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
import logging
import os
import signal
import subprocess
import sys
import threading

ROOT = Path(__file__).resolve().parent.parent
stop_event = threading.Event()


def tick(last_completed_day, *, now=None):
    local = (now or datetime.now(timezone.utc)).astimezone(ZoneInfo('Europe/Istanbul'))
    if local.hour < 9 or local.date() == last_completed_day:
        return last_completed_day
    # Django is loaded only for the daily command, not in this small waiting process.
    # The database ledger makes simultaneous masters/restarts safe and idempotent.
    subprocess.run([sys.executable, 'manage.py', 'check_account_inactivity'], cwd=ROOT,
                   env={**os.environ, 'DJANGO_SETTINGS_MODULE': 'itaudit.settings'},
                   check=True, timeout=120)
    return local.date()


def main():
    for signum in (signal.SIGTERM, signal.SIGINT):
        signal.signal(signum, lambda *_: stop_event.set())
    parent = int(os.environ['INACTIVITY_PARENT_PID'])
    completed = None
    print('Account inactivity scheduler ready: daily 09:00 Europe/Istanbul', flush=True)
    while not stop_event.is_set() and os.getppid() == parent:
        try:
            completed = tick(completed)
        except (subprocess.SubprocessError, OSError):
            logging.exception('09:00 inactivity check failed; retrying next minute')
        stop_event.wait(60)


if __name__ == '__main__':
    main()
