"""Run isolated browser QA without production credentials or learner writes."""
import shutil,tempfile,http.server,functools
from pathlib import Path
qa=Path(__file__).resolve().parent;repo=qa.parents[3]
root=Path(tempfile.mkdtemp(prefix='grc-ad-browser-qa-'))
shutil.copytree(repo/'mobile_web/web',root/'web-features')
shutil.copytree(repo/'mobile_api/demo_assets/ad_auditor',root/'images')
shutil.copy(qa.parent/'package.json',root/'package.json')
shutil.copy(qa/'browser-fixture.html',root/'index.html')
shutil.copy(qa/'browser-fixture.mjs',root/'qa.mjs')
print('QA at http://localhost:8765; mock grading, no production writes',flush=True)
http.server.ThreadingHTTPServer(('127.0.0.1',8765),functools.partial(http.server.SimpleHTTPRequestHandler,directory=str(root))).serve_forever()
