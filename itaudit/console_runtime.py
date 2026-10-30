"""Lifecycle hooks for a private console process in the existing Render service."""
import os,signal,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
_supervisor=None
_inactivity_worker=None

def start(server):
    global _supervisor, _inactivity_worker
    try:
        _inactivity_worker=subprocess.Popen([sys.executable,'-m','itaudit.inactivity_scheduler'],cwd=ROOT,start_new_session=True,env={**os.environ,"INACTIVITY_PARENT_PID":str(os.getpid()),"DJANGO_SETTINGS_MODULE":"itaudit.settings"})
    except OSError:
        server.log.exception("Account inactivity scheduler could not start")
    if os.getenv('CONSOLE_ENABLED','true').lower()!='true':return
    try:_supervisor=subprocess.Popen([sys.executable,'-m','itaudit.console_supervisor'],cwd=ROOT,start_new_session=True,env={**os.environ,"CONSOLE_PARENT_PID":str(os.getpid())})
    except OSError:server.log.exception("Console supervisor could not start; original site remains available.")

def stop(server):
    if _inactivity_worker and _inactivity_worker.poll() is None:
        try: os.killpg(_inactivity_worker.pid, signal.SIGTERM)
        except ProcessLookupError: pass
        try: _inactivity_worker.wait(timeout=10)
        except subprocess.TimeoutExpired: os.killpg(_inactivity_worker.pid, signal.SIGKILL)
    if _supervisor and _supervisor.poll() is None:
        try:os.killpg(_supervisor.pid,signal.SIGTERM)
        except ProcessLookupError:return
        try:_supervisor.wait(timeout=10)
        except subprocess.TimeoutExpired:os.killpg(_supervisor.pid,signal.SIGKILL)
