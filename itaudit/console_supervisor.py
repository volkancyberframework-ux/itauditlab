"""No extra Render service/cron: private app and notification retries share this host."""
import os,subprocess,sys,time,signal
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
_stopping=False
_child=None

def stop(signum,frame):
    global _stopping
    _stopping=True
    if _child and _child.poll() is None:_child.terminate()

def parent_alive():
    return os.getppid()==int(os.environ.get("CONSOLE_PARENT_PID",str(os.getppid())))

def main():
    global _child
    signal.signal(signal.SIGTERM,stop)
    signal.signal(signal.SIGINT,stop)
    main_env={**os.environ,'DJANGO_SETTINGS_MODULE':'itaudit.settings'}
    while not _stopping and parent_alive():
        try:
            subprocess.run([sys.executable,'manage.py','prepare_console'],cwd=ROOT,env=main_env,check=True,timeout=180)
            break
        except (subprocess.SubprocessError,OSError):
            print('Console setup failed; existing ITAudit stays available. Retrying.',flush=True)
            for _ in range(30):
                if _stopping or not parent_alive():return
                time.sleep(1)
    if _stopping or not parent_alive():return
    env={**os.environ,'DJANGO_SETTINGS_MODULE':'config.shared_settings'}
    next_retry=0
    while not _stopping and parent_alive():
        _child=subprocess.Popen([sys.executable,'-m','gunicorn','config.shared_wsgi:application','--bind','unix:'+os.getenv('CONSOLE_SOCKET','/tmp/itaudit-console.sock'),'--workers','1','--threads','2','--timeout','60','--access-logfile','-','--umask','0077'],cwd=ROOT/'municipal_console',env=env)
        while not _stopping and parent_alive() and _child.poll() is None:
            if time.monotonic()>=next_retry:
                try:subprocess.run([sys.executable,'manage.py','send_notifications'],cwd=ROOT/'municipal_console',env={**env,'NOTIFICATION_BATCH_SIZE':'10'},timeout=90,check=True)
                except (subprocess.SubprocessError,OSError):print('Console notification retry deferred.',flush=True)
                next_retry=time.monotonic()+60
            time.sleep(1)
        if not _stopping:time.sleep(3)
    if _child and _child.poll() is None:_child.terminate()

if __name__=='__main__':main()
