"""Copy the verified Flutter release into the Python service's deployed assets."""
from pathlib import Path
import shutil

root = Path(__file__).resolve().parent
source = root.parent / 'mobile' / 'build' / 'web'
if not (source / 'main.dart.js').is_file():
    raise SystemExit('Run flutter build web first.')
shutil.copytree(source, root / 'dist', dirs_exist_ok=True)
