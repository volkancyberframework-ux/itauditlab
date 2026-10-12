from pathlib import Path

from django.conf import settings
from django.core.files import File
from django.core.files.storage import FileSystemStorage


class PrivateVoiceStorage(FileSystemStorage):
    def __init__(self):
        super().__init__(location=settings.MOBILE_VOICE_ROOT, base_url=None)

    # Immutable demo assets stay available across deployments without public media URLs.
    bundled = {
        "demo/access-review.png": "access-review.png",
        "demo/mfa.m4a": "mfa.m4a",
        **{f"first30/evidence_{n:03}.png": f"first30/evidence_{n:03}.png"
           for n in (18,27,38,47,57,68,77,87,97)},
        "first30-v2/evidence_008.png": "first30_v2/evidence_008.png",
        **{f"first30-v2/grc_day_{n:02}.mp3": f"first30_v2/grc_day_{n:02}.mp3" for n in range(1,11)},
    }

    def _open(self, name, mode="rb"):
        try:
            return super()._open(name, mode)
        except FileNotFoundError:
            if name not in self.bundled or mode != "rb":
                raise
            asset = Path(__file__).parent / "demo_assets" / self.bundled[name]
            return File(asset.open(mode), name=name)

    def exists(self, name):
        return super().exists(name) or name in self.bundled

    def url(self, name):
        raise ValueError(
            "Private recordings must be accessed through the authorized API."
        )
