"""Lifecycle hooks for a private console process in the existing Render service."""
import os,signal,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
_supervisor=None

def start(server):
    global _supervisor
    if os.getenv('CONSOLE_ENABLED','true').lower()!='true':return
    try:_supervisor=subprocess.Popen([sys.executable,'-m','itaudit.console_supervisor'],cwd=ROOT,start_new_session=True,env={**os.environ,"CONSOLE_PARENT_PID":str(os.getpid())})
    except OSError:server.log.exception("Console supervisor could not start; original site remains available.")

def stop(server):
    if _supervisor and _supervisor.poll() is None:
        try:os.killpg(_supervisor.pid,signal.SIGTERM)
        except ProcessLookupError:return
        try:_supervisor.wait(timeout=10)
        except subprocess.TimeoutExpired:os.killpg(_supervisor.pid,signal.SIGKILL)
